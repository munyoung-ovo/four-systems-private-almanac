# Phase 0 API 对齐备忘

## lunar_python
- 导入：`from lunar_python import Solar`
- 初始化：`Solar.fromYmdHms(y, m, d, h, min, s).getLunar()`
- 八字：`lunar.getEightChar()` → `ec.getYear/Month/Day/getTime()` （**时柱是 getTime()，不是 getHour()**）
- 宜忌：`lunar.getDayYi()` / `lunar.getDayJi()` → list[str]
- 闰月判断：`lunar.getMonth()` 返回负数（如 -4 = 闰四月），**无 isLeap() 方法**

## iztro_py
- 导入：`from iztro_py import astro`（**包名 iztro-py，模块名 iztro_py，import astro 子模块**）
- 初始化：`astro.by_solar("YYYY-M-D", time_index, "男|女")` → `FunctionalAstrolabe`
- **time_index 是时辰索引(0-12)，不是原始小时数！** 0=早子(00-01) 1=丑(01-03) ... 4=辰(07-09) ... 12=晚子(23-24)
- 转换：`(total_minutes - 60) // 120 + 1`（total_min<60 →0，≥1380 →12）
- 命宫支：`chart.earthly_branch_of_soul_palace`（返回英文枚举如 `weiEarthly`）
- 身宫支：`chart.earthly_branch_of_body_palace`
- 五行局：`chart.five_elements_class`（如 `木三局`）
- 宫位列表：`chart.palaces` → list[FunctionalPalace]，`p.name`/`p.major_stars`/`p.heavenly_stem`/`p.earthly_branch`
- 宫位名/星曜名均为英文枚举，需翻译映射

## pyswisseph
- `swe.SIDM_LAHIRI = 1`（已确认）
- Nakshatra 流程：`swe.set_sid_mode(swe.SIDM_LAHIRI)` → `swe.calc_ut(jd, swe.MOON, swe.FLG_SIDEREAL)` → `lon/30*13.333` → index
- 西占 tropical：**不设 sidereal mode**，直接 `swe.calc_ut(jd, planet, swe.FLG_SPEED)`，取 `result[0][0]`
- Julian Day：`swe.julday(y, m, d, hour_decimal_utc)`，注意入参是 **UTC** 时间
