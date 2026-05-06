# MTK Camera DTS 配置参考

## Camera 主节点
```dts
&camera {
    status = "okay";
};
```

## Seninf (Sensor Interface) 节点
```dts
&seninf {
    status = "okay";
};
```

## Sensor 子节点

### 必需属性
| 属性 | 类型 | 说明 |
|------|------|------|
| compatible | string | 必须匹配驱动中的 compatible |
| reg | u32 | I2C 7位地址 |
| status | string | "okay" 或 "disabled" |

### 电源属性
| 属性 | 类型 | 说明 |
|------|------|------|
| avdd-supply | phandle | 模拟电源 |
| dvdd-supply | phandle | 数字电源 |
| dovdd-supply | phandle | I/O 电源 |

### GPIO 属性
| 属性 | 类型 | 说明 |
|------|------|------|
| reset-gpios | phandle+flags | Reset 引脚 |
| pwdn-gpios | phandle+flags | Power Down 引脚 |

### 时钟属性
| 属性 | 类型 | 说明 |
|------|------|------|
| clocks | phandle | MCLK 时钟源 |
| clock-names | string | 时钟名称，通常为 "mclk" |

### MIPI CSI 属性
| 属性 | 类型 | 说明 |
|------|------|------|
| data-lanes | list | 数据 lane 编号列表 |
| clock-lanes | u32 | 时钟 lane 编号 |

### 可选属性
| 属性 | 类型 | 说明 |
|------|------|------|
| rotation | u32 | 传感器旋转角度 (0/90/180/270) |
| orientation | u32 | 前后摄标识 (0=后摄, 1=前摄) |
| lens-focus | phandle | VCM 驱动节点引用 |
| eeprom | phandle | EEPROM 驱动节点引用 |

## 常见配置错误

1. **I2C 地址错误**: 注意 7位地址和 8位地址的区别，DTS 中使用 7位地址
2. **regulator 缺失**: 必须配置所有需要的电源，否则 probe 会失败
3. **GPIO 配置错误**: 注意 ACTIVE_HIGH/ACTIVE_LOW 的极性
4. **clock 缺失**: MCLK 未配置会导致 Sensor 无法输出 MIPI 信号
5. **status 未设为 okay**: 忘记设置 status 会导致节点不生效
