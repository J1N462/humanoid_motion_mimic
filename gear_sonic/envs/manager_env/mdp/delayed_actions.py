"""제어 지연 랜덤화 액션.

실기에서 명령은 즉시 먹지 않는다 (온보드 실측 20~48 ms). 지연 없이 학습한 정책은
실기에서 균형 보정이 늦게 도착해 과보정으로 발산한다.

MuJoCo 측정 (지연 랜덤화 없이 학습한 현재 정책):
    지연  0 ms  서 있음 (골반 0.435 m)
    지연 20 ms  서 있음 (골반 0.425 m)
    지연 40 ms  넘어짐 (골반 0.283 m)   <- 실기 overrun 구간이 여기에 걸린다

목표 위치를 원형 버퍼에 넣고, 환경마다 뽑은 지연만큼 지난 값을 적용한다.
지연은 에피소드마다 다시 뽑고 에피소드 안에서는 고정한다 (실기 지연도 한 실행
안에서는 안정적이다).

사용 (joint_pos.yaml):
    joint_pos:
      _target_: gear_sonic.envs.manager_env.mdp.delayed_actions.DelayedJointPositionActionCfg
      asset_name: "robot"
      joint_names: [".*"]
      use_default_offset: true
      max_delay_steps: 2        # 제어주기 20ms -> 0~40ms 를 겪으며 배운다
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import torch

from isaaclab.envs.mdp.actions.joint_actions import JointPositionAction
from isaaclab.envs.mdp.actions import actions_cfg
from isaaclab.utils import configclass

if TYPE_CHECKING:
    from isaaclab.envs import ManagerBasedEnv


class DelayedJointPositionAction(JointPositionAction):
    """관절 위치 목표를 0~max_delay_steps tick 늦게 적용한다."""

    def __init__(self, cfg: "DelayedJointPositionActionCfg", env: "ManagerBasedEnv"):
        super().__init__(cfg, env)

        self._buf_len = int(cfg.max_delay_steps) + 1
        # [buf_len, num_envs, action_dim]
        self._delay_buf = torch.zeros(
            self._buf_len, self.num_envs, self.action_dim, device=self.device
        )
        self._head = 0
        self._delay = torch.randint(
            0, self._buf_len, (self.num_envs,), device=self.device, dtype=torch.long
        )
        self._env_idx = torch.arange(self.num_envs, device=self.device)

        # 버퍼를 기본 관절 위치로 채운다 (0 으로 두면 "모든 관절 0" 목표가 나가 로봇을 찢는다)
        default_q = self._asset.data.default_joint_pos[:, self._joint_ids]
        self._delay_buf[:] = default_q.unsqueeze(0)

    def apply_actions(self):
        # 이번 tick 의 목표를 버퍼에 쓴다
        self._delay_buf[self._head] = self.processed_actions
        # 환경마다 자기 지연만큼 지난 값을 읽는다
        idx = (self._head - self._delay) % self._buf_len
        delayed = self._delay_buf[idx, self._env_idx]
        self._asset.set_joint_position_target(delayed, joint_ids=self._joint_ids)
        self._head = (self._head + 1) % self._buf_len

    def reset(self, env_ids: torch.Tensor | slice | None = None) -> None:
        super().reset(env_ids)
        if env_ids is None:
            env_ids = slice(None)
        # 리셋된 환경의 버퍼를 현재 관절 위치로 채운다
        q = self._asset.data.joint_pos[env_ids][:, self._joint_ids]
        self._delay_buf[:, env_ids] = q.unsqueeze(0)
        # 에피소드마다 지연을 다시 뽑는다
        n = self.num_envs if isinstance(env_ids, slice) else len(env_ids)
        self._delay[env_ids] = torch.randint(
            0, self._buf_len, (n,), device=self.device, dtype=torch.long
        )


@configclass
class DelayedJointPositionActionCfg(actions_cfg.JointPositionActionCfg):
    """DelayedJointPositionAction 설정."""

    class_type: type = DelayedJointPositionAction

    max_delay_steps: int = 2
    """지연 상한 (tick). 제어주기 20ms 기준 2 면 0~40ms."""
