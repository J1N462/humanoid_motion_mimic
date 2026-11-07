# humanoid_motion_mimic

Motion imitation on the Unitree G1 from a YouTube video, built on [NVIDIA GR00T-WholeBodyControl](https://github.com/NVlabs/GR00T-WholeBodyControl).
This repository contains only the files I changed in GR00T-WholeBodyControl (base commit `087f9ac`).

## Demo
- Source video: https://youtube.com/shorts/83gk2eQ16Wc?si=V3EW7PIMmvTLhBGK
- Demo: https://youtube.com/shorts/J-RW6SlCspA?feature=share

## Pipeline overview
YouTube video → human motion extraction → G1 retargeting → policy fine-tuning → real-robot deployment
- Motion extraction: GVHMR (video → SMPL motion)
- Retargeting: GMR (motion → G1)
- Training: GR00T-WholeBodyControl `gear_sonic`, fine-tuned from the released SONIC checkpoint on the retargeted motions
- Deployment: GR00T-WholeBodyControl `gear_sonic_deploy/g1_deploy_onnx_ref`

## Based on NVIDIA GR00T-WholeBodyControl
The training stack (`gear_sonic`) and the deployment program (`gear_sonic_deploy/g1_deploy_onnx_ref`: inference loop, zmq/gamepad/ros2 input, reference motion playback, policy/encoder wrappers, local motion planner) are NVIDIA's code. The deployment files in this repository are upstream files with my modifications described below.

## My changes
Verified with `git diff` against upstream commit `087f9ac`: 10 files, +244 / −56 lines. `delayed_actions.py` is the only new file; all other files are modified upstream files.

### 1. Action-delay randomization for training (`gear_sonic/`)
- `envs/manager_env/mdp/delayed_actions.py` (new) — `DelayedJointPositionAction`: joint position targets go through a ring buffer and are applied 0–`max_delay_steps` control ticks late. The delay is resampled every episode and fixed within an episode.
- `envs/manager_env/mdp/__init__.py` — registers the new term (+1 line).
- `config/manager_env/actions/terms/joint_pos.yaml` — switches the joint position action to `DelayedJointPositionActionCfg` with `max_delay_steps: 2` (0–40 ms at a 20 ms control period).

### 2. ONNX Runtime (CPU) backend option for deployment (`gear_sonic_deploy/`)
Upstream runs the encoder, policy and planner on TensorRT. I added a compile-time option, `USE_ORT_INFERENCE`, that runs all three on ONNX Runtime (CPU) with no TensorRT dependency. TensorRT stays the default.
- `CMakeLists.txt` — adds the `USE_ORT_INFERENCE` option (default OFF); TensorRT is only required when it is OFF.
- `src/CMakeLists.txt` — builds `TRTInference` only for the TensorRT backend.
- `src/g1/g1_deploy_onnx_ref/CMakeLists.txt` — links TensorRT libraries only for the TensorRT backend; adds a `BUILD_TESTS` option to skip the googletest download on offline machines.
- `include/control_policy.hpp`, `include/encoder.hpp` — select the inference backend at compile time; skip ONNX→TensorRT conversion and CUDA graph capture when using ONNX Runtime.
- `src/g1_deploy_onnx_ref.cpp` — uses the ONNX planner (`LocalMotionPlannerONNX`) when `USE_ORT_INFERENCE` is set (+16 lines).
- `include/localmotion_kplanner_onnx.hpp` — re-enables this previously unused upstream planner backend and accepts planner model version 2 (same inputs as version 1).

Note: the ONNX Runtime backend also needs `ort_inference_engine.hpp` (`OrtInferenceEngine`), which is not yet included in this repository. The default TensorRT build does not need it.

## Usage
1. Check out NVIDIA GR00T-WholeBodyControl at commit `087f9ac` and copy the files from this repository over the same paths.
2. Build `gear_sonic_deploy/` (add `-DUSE_ORT_INFERENCE=ON` for the ONNX Runtime backend) and run it on the G1:
   ```bash
   ./g1_deploy_onnx_ref <net-if> policy/single_frame/model.onnx reference/<motion>/ \
       --input-type zmq --zmq-host <robot-ip> --zmq-port 5556 --zmq-topic pose
   ```

## License / attribution
- Upstream: **NVlabs/GR00T-WholeBodyControl** — source code under the Apache License 2.0.
- The files in this repository are derivative works of the upstream project and are likewise licensed under the Apache License 2.0. See [`LICENSE`](./LICENSE) and [`NOTICE`](./NOTICE).
- Changes: see "My changes" above.
- Model weights (checkpoints) are not included.
