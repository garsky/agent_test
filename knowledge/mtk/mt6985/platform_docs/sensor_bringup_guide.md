# MTK Camera Sensor 点亮指南

## 点亮流程

### 1. 硬件确认
- 确认 Sensor 型号和规格
- 确认模组连接方式 (MIPI CSI-2)
- 确认 I2C 地址 (参考 Sensor Datasheet SADDR 引脚配置)
- 确认上电时序 (AVDD/DVDD/DOVDD 顺序和延时)

### 2. DTS 配置
在对应平台的 DTS 中添加 Sensor 节点：

```dts
&camera {
    status = "okay";
};

&i2c0 {
    camera_sensor: sensor@10 {
        compatible = "mediatek,camera-sensor";
        reg = <0x10>;  /* I2C 7位地址 */
        
        avdd-supply = <&mt6357_vcamaf>;
        dvdd-supply = <&mt6357_vcamd>;
        dovdd-supply = <&mt6357_vcamio>;
        
        reset-gpios = <&pio 15 GPIO_ACTIVE_LOW>;
        pwdn-gpios = <&pio 16 GPIO_ACTIVE_HIGH>;
        
        clocks = <&topckgen CLK_TOP_CAMTG>;
        clock-names = "mclk";
        
        data-lanes = <1 2 3 4>;
        clock-lanes = <0>;
        
        status = "okay";
    };
};
```

### 3. Sensor Driver 添加
- 在 `kernel-4.14/drivers/misc/mediatek/imgsensor/src/` 下添加 Sensor 驱动
- 注册到 Sensor list
- 配置 Sensor mode (分辨率、帧率、输出格式)

### 4. 上电时序
典型上电时序：
```
1. DOVDD 上电
2. 延时 1-5ms
3. DVDD 上电
4. 延时 1-5ms
5. AVDD 上电
6. 延时 1-5ms
7. MCLK 输出
8. 延时 1-5ms
9. Reset GPIO 拉高
10. 延时 1-5ms
11. PWDN GPIO 拉低
12. 延时 5-20ms
13. I2C 通信开始
```

### 5. 验证步骤
1. 检查 I2C 通信: `i2cdetect -y 0`
2. 检查 Sensor probe: `dmesg | grep sensor`
3. 检查 /dev/videoX 节点: `ls /dev/video*`
4. 抓帧测试: 使用 camera HAL 测试工具

## 常见问题

### I2C 通信失败
- 检查 I2C 地址是否正确
- 检查上电时序是否正确
- 检查 I2C 总线是否被其他设备占用
- 用示波器测量 I2C 波形

### Sensor 无法识别
- 检查 compatible 字符串
- 检查 Sensor 驱动是否编译进内核
- 检查 DTS 节点 status 是否为 "okay"

### 黑屏
- 检查 MIPI CSI 配置 (lane数、速率)
- 检查 Sensor 输出格式
- 检查 ISP 配置
