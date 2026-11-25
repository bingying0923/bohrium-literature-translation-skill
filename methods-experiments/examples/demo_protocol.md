# Steps

1. 过滤水样（input: 原始水样；output: 滤液；condition: 0.45 µm 滤膜）
2. 富集铅离子（input: 滤液；output: 富集膜；condition: 5 min 孵育）
3. 拍照记录显色（input: 富集膜；output: RGB 图像；condition: 固定光照）
4. 拟合标准曲线（input: 标准系列；output: 曲线参数；condition: 线性拟合）

# Parameters

| 名称 | 取值 | 单位 | 作用对象 | 来源 |
|---|---|---|---|---|
| incubation_time | 5 | min | 富集步骤 | protocol |
| membrane_pore | 0.45 | µm | 过滤步骤 | protocol |
| camera_gain | 1.2 | - | 显色拍照 | config |

# Datasets

- name: 城市水样; version: v1.0; n: 36; split: 24/6/6; preprocess: 0.45 µm 过滤; use: 训练/验证/测试

# Reproduce

- code_version: git-abc123
- env: python 3.11, numpy 2.0
- command: python run.py --config config.json
- seed: 42
- repeats: 3
