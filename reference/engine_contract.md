# 引擎回参结构

LLM 解读只能引用真实字段，不要臆造 key。计算口径：

- 八字：立春分年界，12 节气分月界，23:00 换日。
- Vedic：Lahiri ayanamsa 固定。

## `profile["bazi"]`

```text
pillars{year,month,day,hour}
day_master
day_master_strength
strength_score
strength_confidence
strength_near_boundary
strength_breakdown[]
yong_shen[]
ji_shen[]
tiaohou_yong_shen[]
ge_ju
ten_gods{year,month,time}
tai_sui_branch
nayin{}
luck{direction,start,dayun[],current_dayun,current_liunian}
time_adjustment{enabled,input_time,effective_time,longitude_correction_minutes,equation_of_time_minutes,total_correction_minutes}
boundary_warnings[{type,minutes_from_boundary,note}]
degraded
```

八字默认按出生地经度和时区做真太阳时校正。`effective_time` 是实际用于排盘的时间；接近时辰或 23:00 换日边界时必须提示边界待复核。用户明确要求按钟表时间盘时，可通过 `use_true_solar=False` 关闭校正。
`luck` 提供大运与当前流年，深度命盘和阶段判断优先引用 `current_dayun` / `current_liunian`。

## `personalize.build(profile, day)`

```text
date
score
tier
personal_yi[{item,strength,reason}]
personal_ji[{item,strength,reason}]
flags{冲日主,冲流年太岁,贵人到,驿马动,桃花到,用神得力}
score_breakdown[{label,delta,detail}]
confidence
near_boundary
degraded
degrade_reason
short_sign
```

## `daily.build(date)`

```text
date
ganzhi{year,month,day}
base_yi[]
base_ji[]
shensha[]
zhi_xing
panchanga{nakshatra,tithi,is_waxing,yoga,karana}
transits[{planet,sign,longitude}]
```

## `resonance.analyze_date(profile, act, date)`

```text
date
act
resonance_strength
is_destined_moment
votes{bazi,ziwei,vedic,western:{stance,basis,precision}}
conflict{type,note,why_both,avoid_systems} | null
```

冲突时参考精度排序：Vedic 日-时级 > 八字日级 > Western 天级 > 紫微年-月级。

## 健壮性

`ics_builder` 和 `find_best_dates` 返回错误项时可能没有 `resonance_strength`。下游必须过滤：

```python
results = [r for r in results if "resonance_strength" in r]
```

拿不到确定性数据时降级标注，不靠 LLM 补排盘。

## `profile["western"]`

```text
sun
moon
ascendant
mc
planets{planet:{longitude,sign,degree,speed,retrograde}}
natal_aspects[{planet1,planet2,aspect,angle,orb,orb_limit,strength}]
ascendant_longitude
mc_longitude
house_cusps[]
degraded
```

`strength` 是相位精确度，0-1，越接近 1 越贴近精确相位。`retrograde` 用于判断文书、关系和行动反复。
`western.transit_hits(western_chart, date)` 返回行运行星触发本命太阳/月亮/金星/火星/上升/天顶的主要相位。

## `profile["ziwei"]`

```text
soul_palace
body_palace
five_elements_class
palaces[{index,name,heavenly_stem,earthly_branch,major_stars,minor_stars}]
palace_by_name{name: palace}
horoscope_layers{decadal,yearly,monthly,daily}
degraded
```

按具体主题取宫位时优先用 `palace_by_name`，不要按数组顺序猜宫。
`horoscope_layers` 提供大限、流年、流月、流日四层：每层都有 `flow_soul_palace`、`flow_roles`、`transforms`。紫微详细版优先用这里取四化落宫和流动命宫。

## `profile["vedic"]`

```text
moon_nakshatra
moon_pada
moon_longitude_sidereal
ascendant_nak
vimshottari{mahadasha,mahadasha_remaining_years,next_mahadasha,timeline[]}
ashtakavarga
ayanamsa
degraded
```

`vimshottari.timeline` 是 Mahadasha 时间线；当前阶段解读可与八字 `luck.current_dayun` 交叉印证。

## `fusion.fuse_date(profile, act, date)`

```text
date
act
topic
overall
score
weight_policy
system_order[]
confidence
convergence{favor,neutral,avoid,dominant}
conflict{type,favor_systems,avoid_systems,note} | null
state
best_actions[]
avoid_actions[]
risks[]
timing
one_liner
evidence[{system,signal,role,time_scale,weight,reason}]
raw{personalize,resonance}
```

`fusion` 是最终面向用户的统一语言层。用户问“能不能做”时，优先用 `one_liner`、`best_actions`、`avoid_actions` 和 `risks`，不要直接罗列四系统投票。

排序短码：

```text
a = 默认排序占卜
b + 数字排序；1八字 2紫微 3西占 4印占
```
