# humanoid_motion_mimic

## 데모
- 원본영상 : https://youtube.com/shorts/83gk2eQ16Wc?si=V3EW7PIMmvTLhBGK
- 데모 : https://youtube.com/shorts/J-RW6SlCspA?feature=share

## 파이프라인 개요
유튜브 영상 → 사람 모션 추출 → G1 리타게팅 → 정책 학습 → **실기 ONNX 배포**
- 모션 추출: GVHMR (video → SMPL motion)
- 리타게팅: GMR (motion → G1 bones)
- 학습/환경: GR00T-WholeBodyControl `gear_sonic`
- **실기 배포: 이 저장소의 `gear_sonic_deploy/g1_deploy_onnx_ref`**

## 내 기여 내용

### 1. 학습 환경 (`gear_sonic/`)
- `envs/manager_env/mdp/delayed_actions.py` — **액션 지연(delayed action) MDP term 신규 구현** (sim-to-real 갭 완화용 액션 딜레이 모델링)
- `envs/manager_env/mdp/__init__.py` — 위 term 등록
- `config/manager_env/actions/terms/joint_pos.yaml` — joint position action term 설정 조정

### 2. 실기 배포 (`gear_sonic_deploy/g1_deploy_onnx_ref/`)
G1에서 학습된 정책을 **ONNX 런타임으로 실시간 추론·배포**하는 참조 구현:
- `src/g1_deploy_onnx_ref.cpp` — 배포 메인 (ONNX 추론 루프, zmq/gamepad/ros2 입력, reference motion 재생)
- `include/control_policy.hpp` — 정책 추론 래퍼
- `include/encoder.hpp` — 관측 인코더
- `include/localmotion_kplanner_onnx.hpp` — local motion k-planner ONNX 연동
- `CMakeLists.txt` (×3) — ONNX Runtime 링크 등 빌드 구성

## 사용법
1. 이 저장소의 파일들을 GR00T 트리의 동일 경로에 덮어씁니다.
2. `gear_sonic_deploy/`를 빌드해 G1 실기에 배포합니다.
   ```bash
   ./g1_deploy_onnx_ref <net-if> policy/single_frame/model.onnx reference/<motion>/ \
       --input-type zmq --zmq-host <robot-ip> --zmq-port 5556 --zmq-topic pose
   ```

## 라이선스 / 출처
- 원본: **NVlabs/GR00T-WholeBodyControl** — 소스코드는 Apache License 2.0.
- 이 저장소의 파일들은 위 원본의 **파생물(derivative)** 이며 동일하게 **Apache License 2.0**을 따릅니다. 원본 라이선스 전문은 [`LICENSE`](./LICENSE) 참조.
- 변경 사항: `gear_sonic` 액션/딜레이 관련 수정, `gear_sonic_deploy/g1_deploy_onnx_ref` 배포 코드 수정·추가 (상세는 위 "내 기여 내용").
- 모델 가중치(체크포인트)는 포함하지 않습니다.
