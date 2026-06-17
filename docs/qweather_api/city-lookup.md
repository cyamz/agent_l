# 城市搜索 API（GeoAPI City Lookup）

> 来源：<https://dev.qweather.com/docs/api/geoapi/city-lookup/>

## 接口说明

城市搜索 API 提供全球地理位置、全球城市搜索服务，支持经纬度坐标反查、多语言、模糊搜索等功能。

天气数据是基于地理位置的数据，因此获取天气之前需要先知道具体的位置信息。使用城市搜索，可获取到该城市的基本信息，包括城市的 Location ID（你需要这个 ID 去查询天气）、多语言名称、经纬度、时区、海拔、Rank 值、归属上级行政区域、所在行政区域等。

另外，城市搜索也可以帮助在你的 APP 中实现模糊搜索，用户只需要输入 1-2 个字即可获得结果。

## 请求路径

```
GET https://{your_api_host}/geo/v2/city/lookup
```

## 认证方式

```
Authorization: Bearer {your_token}
```

> 将 `{your_token}` 替换为你的 JWT 身份认证，`{your_api_host}` 替换为你的 API Host。

## 请求参数

| 参数 | 必选 | 说明 |
| --- | --- | --- |
| `location` | 是 | 需要查询地区的名称，支持文字、以英文逗号分隔的经度,纬度坐标（十进制，最多支持小数点后两位）、LocationID 或 Adcode（仅限中国城市）。例如 `location=北京` 或 `location=116.41,39.92` |
| `adm` | 否 | 城市的上级行政区划，可设定只在某个行政区划范围内进行搜索，用于排除重名城市或对结果进行过滤。例如 `adm=beijing` |
| `range` | 否 | 搜索范围，可设定只在某个国家或地区范围内进行搜索，国家和地区名称需使用 ISO 3166 所定义的国家代码。不设置则在所有城市搜索。例如 `range=cn` |
| `number` | 否 | 返回结果的数量，取值范围 1-20，默认返回 10 个结果 |
| `lang` | 否 | 多语言设置 |

### 模糊搜索

当 `location` 传递文字时，支持模糊搜索，即用户可以只输入城市名称一部分进行搜索，最少一个汉字或 2 个字符，结果将按照相关性和 Rank 值进行排列。例如 `location=bei`，将返回与 bei 相关性最强的若干结果，包括黎巴嫩的贝鲁特和中国的北京市。

### 重名处理

当 `location` 传递文字时，可能会出现重名城市，此时会根据 Rank 值排序返回所有结果。可通过 `adm` 参数进一步确定需要查询的城市或地区，例如 `location=西安&adm=黑龙江`。

- `location=chaoyang&adm=beijing` → 只返回北京市的朝阳区
- `location=chaoyang` → 返回北京市朝阳区、辽宁省朝阳市、长春市朝阳区

## 请求示例

```bash
curl -X GET --compressed \
  -H 'Authorization: Bearer your_token' \
  'https://your_api_host/geo/v2/city/lookup?location=beij'
```

## 返回数据

返回数据为 JSON 格式并进行了 Gzip 压缩。

```json
{
  "code": "200",
  "location": [
    {
      "name": "北京",
      "id": "101010100",
      "lat": "39.90499",
      "lon": "116.40529",
      "adm2": "北京",
      "adm1": "北京市",
      "country": "中国",
      "tz": "Asia/Shanghai",
      "utcOffset": "+08:00",
      "isDst": "0",
      "type": "city",
      "rank": "10",
      "fxLink": "https://www.qweather.com/weather/beijing-101010100.html"
    }
  ],
  "refer": {
    "sources": ["QWeather"],
    "license": ["QWeather Developers License"]
  }
}
```

### 字段说明

| 字段 | 说明 |
| --- | --- |
| `code` | 状态码，请参考状态码文档 |
| `location[].name` | 地区/城市名称 |
| `location[].id` | 地区/城市 ID（**LocationID，查询天气时使用**） |
| `location[].lat` | 地区/城市纬度 |
| `location[].lon` | 地区/城市经度 |
| `location[].adm2` | 地区/城市的上级行政区划名称 |
| `location[].adm1` | 地区/城市所属一级行政区域 |
| `location[].country` | 地区/城市所属国家名称 |
| `location[].tz` | 地区/城市所在时区 |
| `location[].utcOffset` | 地区/城市目前与 UTC 时间偏移的小时数 |
| `location[].isDst` | 是否当前处于夏令时。`1` 是，`0` 否 |
| `location[].type` | 地区/城市的属性 |
| `location[].rank` | 地区评分 |
| `location[].fxLink` | 该地区的天气预报网页链接，便于嵌入网站或应用 |
| `refer.sources` | 原始数据来源，**可能为空** |
| `refer.license` | 数据许可或版权声明，**可能为空** |
