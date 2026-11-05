"""Action with randomized control delay.

On the real robot, commands do not take effect immediately (measured onboard: 20~48 ms).
A policy trained without delay receives its balance corrections late on the real robot
and diverges from over-correction.

MuJoCo measurements (current policy, trained without delay randomization):
    delay  0 ms  standing (pelvis 0.435 m)
    delay 20 ms  standing (pelvis 0.425 m)
    delay 40 ms  fell     (pelvis 0.283 m)   <- the real-robot overrun range falls here

Target positions are pushed into a ring buffer, and each env applies the value from
its sampled number of steps ago. The delay is resampled every episode and fixed within
an episode (real-robot delay is also stable within one run).

Usage (joint_pos.yaml):
    joint_pos:
      _target_: gear_sonic.envs.manager_env.mdp.delayed_actions.DelayedJointPositionActionCfg
      asset_name: "robot"
      joint_names: [".*"]
      use_default_offset: true
      max_delay_steps: 2        # 20 ms control period -> trains under 0~40 ms delay
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
    """Applies joint position targets 0~max_delay_steps ticks late."""

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

        # Fill the buffer with default joint positions (leaving zeros would send an "all joints 0" target and tear the robot apart)
        default_q = self._asset.data.default_joint_pos[:, self._joint_ids]
        self._delay_buf[:] = default_q.unsqueeze(0)

    def apply_actions(self):
        # Write this tick's target into the buffer
        self._delay_buf[self._head] = self.processed_actions
        # Each env reads the value from its own delay ago
        idx = (self._head - self._delay) % self._buf_len
        delayed = self._delay_buf[idx, self._env_idx]
        self._asset.set_joint_position_target(delayed, joint_ids=self._joint_ids)
        self._head = (self._head + 1) % self._buf_len

    def reset(self, env_ids: torch.Tensor | slice | None = None) -> None:
        super().reset(env_ids)
        if env_ids is None:
            env_ids = slice(None)
        # Fill the buffer of reset envs with their current joint positions
        q = self._asset.data.joint_pos[env_ids][:, self._joint_ids]
        self._delay_buf[:, env_ids] = q.unsqueeze(0)
        # Resample the delay every episode
        n = self.num_envs if isinstance(env_ids, slice) else len(env_ids)
        self._delay[env_ids] = torch.randint(
            0, self._buf_len, (n,), device=self.device, dtype=torch.long
        )


@configclass
class DelayedJointPositionActionCfg(actions_cfg.JointPositionActionCfg):
    """Config for DelayedJointPositionAction."""

    class_type: type = DelayedJointPositionAction

    max_delay_steps: int = 2
    """Maximum delay (ticks). With a 20 ms control period, 2 means 0~40 ms."""
