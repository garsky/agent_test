# MTK Camera 常见错误及解决方案

## I2C 相关错误

### i2c_transfer failed / NACK
**现象**: dmesg 显示 `i2c-0: i2c transfer failed, addr=0x10, NACK`
**可能原因**:
1. I2C 地址配置错误
2. 上电时序不正确，Sensor 未就绪
3. I2C 总线被其他设备占用
4. 硬件连接问题 (SDA/SCL 悬空或短路)

**排查步骤**:
1. 确认 Sensor Datasheet 中的 I2C 地址
2. 检查上电时序是否符合要求
3. 使用 `i2cdetect` 扫描总线
4. 示波器测量 I2C 波形

### i2c timeout
**现象**: `i2c-0: controller timed out`
**可能原因**:
1. I2C 总线死锁
2. 上拉电阻缺失或阻值不当
3. 总线频率过高

## MIPI CSI 相关错误

### CSI overflow
**现象**: `seninf: csi overflow detected`
**可能原因**:
1. MIPI 数据速率过高
2. HS-SETTLE 参数配置不当
3. FIFO 溢出

**解决方案**:
1. 降低 MIPI 数据速率
2. 调整 HS-SETTLE 参数
3. 检查 Sensor 输出格式是否匹配

### MIPI CRC error
**现象**: `mipi: crc error detected`
**可能原因**:
1. 信号完整性问题
2. MIPI 线路阻抗不匹配
3. EMI 干扰

## 电源相关错误

### regulator_enable failed
**现象**: `regulator_enable: failed to enable avdd`
**可能原因**:
1. DTS 中 regulator 配置错误
2. PMIC 驱动未加载
3. 电源域未正确关联

**解决方案**:
1. 检查 DTS 中 xxx-supply 属性
2. 确认 PMIC 驱动已加载
3. 检查 power-domain 配置

## 时钟相关错误

### clk_prepare failed
**现象**: `clk_prepare: failed to prepare mclk`
**可能原因**:
1. DTS 中 clocks 属性配置错误
2. 时钟源未使能
3. CCF (Common Clock Framework) 配置问题

## Sensor 相关错误

### sensor probe failed
**现象**: `camera_sensor: probe failed, ret=-5`
**可能原因**:
1. I2C 通信失败
2. Sensor ID 不匹配
3. 上电时序不正确
4. Sensor 驱动未编译

### sensor not found
**现象**: `camera: no sensor found`
**可能原因**:
1. DTS 中未配置 Sensor 节点
2. compatible 字符串不匹配
3. Sensor 驱动未注册
