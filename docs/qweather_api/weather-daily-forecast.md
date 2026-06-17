# 每日天气预报 API（Weather Daily Forecast）

> 来源：<https://dev.qweather.com/docs/api/weather/weather-daily-forecast/>

## 接口说明

每日天气预报 API，提供全球城市未来 3-30 天天气预报，包括：日出日落、月升月落、最高最低温度、天气白天和夜间状况、风力、风速、风向、相对湿度、大气压强、降水量、露点温度、紫外线强度、能见度等。

## 请求路径

```
GET https://{your_api_host}/v7/weather/{days}
```

## 认证方式

```
Authorization: Bearer {your_token}
```

> 将 `{your_token}` 替换为你的 JWT 身份认证，`{your_api_host}` 替换为你的 API Host。

## 请求参数

### 路径参数

| 参数 | 必选 | 说明 |
| --- | --- | --- |
| `days` | 是 | 预报天数，支持最多 30 天预报。可选值：`3d`（3 天）、`7d`（7 天）、`10d`（10 天）、`15d`（15 天）、`30d`（30 天） |

### 查询参数

| 参数 | 必选 | 说明 |
| --- | --- | --- |
| `location` | 是 | 需要查询地区的 LocationID 或以英文逗号分隔的经度,纬度坐标（十进制，最多支持小数点后两位），LocationID 可通过 GeoAPI 获取。例如 `location=101010100` 或 `location=116.41,39.92` |
| `lang` | 否 | 多语言设置 |
| `unit` | 否 | 数据单位设置，可选值：`unit=m`（公制单位，默认）、`unit=i`（英制单位） |

## 请求示例

```bash
curl -X GET --compressed \
  -H 'Authorization: Bearer your_token' \
  'https://your_api_host/v7/weather/3d?location=101010100'
```

## 返回数据

返回数据为 JSON 格式并进行了 Gzip 压缩。`daily` 数组中每个元素对应一天的预报。

```json
{
  "code": "200",
  "updateTime": "2021-11-15T16:35+08:00",
  "fxLink": "http://hfx.link/2ax1",
  "daily": [
    {
      "fxDate": "2021-11-15",
      "sunrise": "06:58",
      "sunset": "16:59",
      "moonrise": "15:16",
      "moonset": "03:40",
      "moonPhase": "盈凸月",
      "moonPhaseIcon": "803",
      "tempMax": "12",
      "tempMin": "-1",
      "iconDay": "101",
      "textDay": "多云",
      "iconNight": "150",
      "textNight": "晴",
      "wind360Day": "45",
      "windDirDay": "东北风",
      "windScaleDay": "1-2",
      "windSpeedDay": "3",
      "wind360Night": "0",
      "windDirNight": "北风",
      "windScaleNight": "1-2",
      "windSpeedNight": "3",
      "humidity": "65",
      "precip": "0.0",
      "pressure": "1020",
      "vis": "25",
      "cloud": "4",
      "uvIndex": "3"
    }
  ],
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
| `daily.fxDate` | 预报日期 |
| `daily.sunrise` | 日出时间，**在高纬度地区可能为空** |
| `daily.sunset` | 日落时间，**在高纬度地区可能为空** |
| `daily.moonrise` | 当天月升时间，**可能为空** |
| `daily.moonset` | 当天月落时间，**可能为空** |
| `daily.moonPhase` | 月相名称 |
| `daily.moonPhaseIcon` | 月相图标代码，另请参考天气图标项目 |
| `daily.tempMax` | 预报当天最高温度 |
| `daily.tempMin` | 预报当天最低温度 |
| `daily.iconDay` | 预报白天天气状况的图标代码 |
| `daily.textDay` | 预报白天天气状况文字描述，包括阴晴雨雪等天气状态的描述 |
| `daily.iconNight` | 预报夜间天气状况的图标代码 |
| `daily.textNight` | 预报晚间天气状况文字描述 |
| `daily.wind360Day` | 预报白天风向 360 角度 |
| `daily.windDirDay` | 预报白天风向 |
| `daily.windScaleDay` | 预报白天风力等级 |
| `daily.windSpeedDay` | 预报白天风速，公里/小时 |
| `daily.wind360Night` | 预报夜间风向 360 角度 |
| `daily.windDirNight` | 预报夜间风向 |
| `daily.windScaleNight` | 预报夜间风力等级 |
| `daily.windSpeedNight` | 预报夜间风速，公里/小时 |
| `daily.precip` | 预报当天总降水量，默认单位：毫米 |
| `daily.uvIndex` | 紫外线强度指数 |
| `daily.humidity` | 相对湿度，百分比数值 |
| `daily.pressure` | 大气压强，默认单位：百帕 |
| `daily.vis` | 能见度，默认单位：公里 |
| `daily.cloud` | 云量，百分比数值，**可能为空** |
| `refer.sources` | 原始数据来源，或数据源说明，**可能为空** |
| `refer.license` | 数据许可或版权声明，**可能为空** |

## 典型调用流程

通常先调用[城市搜索 API](./city-lookup.md) 拿到目标城市的 `LocationID`，再用该 ID 配合预报天数（如 `3d`/`7d`）调用本接口获取每日天气预报。
