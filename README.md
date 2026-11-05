# humanoid_motion_mimic

## Demo
- Source video: https://youtube.com/shorts/83gk2eQ16Wc?si=V3EW7PIMmvTLhBGK
- Demo: https://youtube.com/shorts/J-RW6SlCspA?feature=share

## Pipeline overview
YouTube video → human motion extraction → G1 retargeting → policy training → **real-robot ONNX deployment**
- Motion extraction: GVHMR (video → SMPL motion)
- Retargeting: GMR (motion → G1 bones)
- Training/environment: GR00T-WholeBodyControl `gear_sonic`
- **Real-robot deployment: `gear_sonic_deploy/g1_deploy_onnx_ref` in this repository**

## My contributions

### 1. Training environment (`gear_sonic/`)
- `envs/manager_env/mdp/delayed_actions.py` — **new delayed-action MDP term** (models action delay to reduce the sim-to-real gap)
- `envs/manager_env/mdp/__init__.py` — registers the term above
- `config/manager_env/actions/terms/joint_pos.yaml` — adjusted joint position action term settings

### 2. Real-robot deployment (`gear_sonic_deploy/g1_deploy_onnx_ref/`)
Reference implementation for **real-time ONNX Runtime inference and deployment** of the trained policy on the G1:
- `src/g1_deploy_onnx_ref.cpp` — deployment main (ONNX inference loop, zmq/gamepad/ros2 input, reference motion playback)
- `include/control_policy.hpp` — policy inference wrapper
- `include/encoder.hpp` — observation encoder
- `include/localmotion_kplanner_onnx.hpp` — local motion k-planner ONNX integration
- `CMakeLists.txt` (×3) — build configuration, including ONNX Runtime linking

## Usage
1. Copy the files in this repository over the same paths in the GR00T tree.
2. Build `gear_sonic_deploy/` and deploy it to the G1.
   ```bash
   ./g1_deploy_onnx_ref <net-if> policy/single_frame/model.onnx reference/<motion>/ \
       --input-type zmq --zmq-host <robot-ip> --zmq-port 5556 --zmq-topic pose
   ```

## License / attribution
- Upstream: **NVlabs/GR00T-WholeBodyControl** — source code under the Apache License 2.0.
- The files in this repository are **derivative works** of the upstream project and are likewise licensed under the **Apache License 2.0**. See [`LICENSE`](./LICENSE) for the full upstream license text.
- Changes: action/delay changes in `gear_sonic`, and modifications/additions to the deployment code in `gear_sonic_deploy/g1_deploy_onnx_ref` (details under "My contributions" above).
- Model weights (checkpoints) are not included.
