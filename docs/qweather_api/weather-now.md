# 实时天气 API（Weather Now）

> 来源：<https://dev.qweather.com/docs/api/weather/weather-now/>

## 接口说明

获取中国 3000+ 市县区和海外 20 万个城市实时天气数据，包括实时温度、体感温度、风力风向、相对湿度、大气压强、降水量、能见度、露点温度、云量等。

> **注意：** 实况数据均为近实时数据，相比真实的物理世界有 5-20 分钟的延迟，请根据实况数据中的 `obsTime` 确定数据对应的准确时间。

## 请求路径

```
GET https://{your_api_host}/v7/weather/now
```

## 认证方式

```
Authorization: Bearer {your_token}
```

> 将 `{your_token}` 替换为你的 JWT 身份认证，`{your_api_host}` 替换为你的 API Host。

## 请求参数

| 参数 | 必选 | 说明 |
| --- | --- | --- |
| `location` | 是 | 需要查询地区的 LocationID 或以英文逗号分隔的经度,纬度坐标（十进制，最多支持小数点后两位），LocationID 可通过 GeoAPI 获取。例如 `location=101010100` 或 `location=116.41,39.92` |
| `lang` | 否 | 多语言设置 |
| `unit` | 否 | 数据单位设置，可选值：`unit=m`（公制单位，默认）、`unit=i`（英制单位） |

## 请求示例

```bash
curl -X GET --compressed \
  -H 'Authorization: Bearer your_token' \
  'https://your_api_host/v7/weather/now?location=101010100'
```

## 返回数据

返回数据为 JSON 格式并进行了 Gzip 压缩。

```json
{
  "code": "200",
  "updateTime": "2020-06-30T22:00+08:00",
  "fxLink": "http://hfx.link/2ax1",
  "now": {
    "obsTime": "2020-06-30T21:40+08:00",
    "temp": "24",
    "feelsLike": "26",
    "icon": "101",
    "text": "多云",
    "wind360": "123",
    "windDir": "东南风",
    "windScale": "1",
    "windSpeed": "3",
    "humidity": "72",
    "precip": "0.0",
    "pressure": "1003",
    "vis": "16",
    "cloud": "10",
    "dew": "21"
  },
  "refer": {
    "sources": ["QWeather", "NMC", "ECMWF"],
    "license": ["QWeather Developers License"]
  }
}
```

### 字段说明

| 字段 | 说明 |
| --- | --- |
| `code` | 状态码，请参考状态码文档 |
| `updateTime` | 当前 API 的最近更新时间 |
| `fxLink` | 当前数据的响应式页面，便于嵌入网站或应用 |
| `now.obsTime` | 数据观测时间 |
| `now.temp` | 温度，默认单位：摄氏度 |
| `now.feelsLike` | 体感温度，默认单位：摄氏度 |
| `now.icon` | 天气状况的图标代码，另请参考天气图标项目 |
| `now.text` | 天气状况的文字描述，包括阴晴雨雪等天气状态的描述 |
| `now.wind360` | 风向 360 角度 |
| `now.windDir` | 风向 |
| `now.windScale` | 风力等级 |
| `now.windSpeed` | 风速，公里/小时 |
| `now.humidity` | 相对湿度，百分比数值 |
| `now.precip` | 过去 1 小时降水量，默认单位：毫米 |
| `now.pressure` | 大气压强，默认单位：百帕 |
| `now.vis` | 能见度，默认单位：公里 |
| `now.cloud` | 云量，百分比数值，**可能为空** |
| `now.dew` | 露点温度，**可能为空** |
| `refer.sources` | 原始数据来源，或数据源说明，**可能为空** |
| `refer.license` | 数据许可或版权声明，**可能为空** |

## 典型调用流程

通常先调用[城市搜索 API](./city-lookup.md) 拿到目标城市的 `LocationID`，再用该 ID 调用本接口获取实时天气。
