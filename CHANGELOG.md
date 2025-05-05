# Changelog

## [0.14.0](https://github.com/chu-shen/BangumiKomga/compare/v0.13.0...v0.14.0) (2025-05-05)


### Features

* prepare for api key ([ea9d9e8](https://github.com/chu-shen/BangumiKomga/commit/ea9d9e8d2e25d94e215215ce8ba673599b7c2939))
* 添加`get_new_added_series()`函数, 以支持新增的`refresh_partial_metadata()` ([#64](https://github.com/chu-shen/BangumiKomga/issues/64)) ([9f65a9f](https://github.com/chu-shen/BangumiKomga/commit/9f65a9fe2817cff2fca5c7753da8c0e521341900))
* 添加Archive索引读取器 ([#60](https://github.com/chu-shen/BangumiKomga/issues/60)) ([32a5ab3](https://github.com/chu-shen/BangumiKomga/commit/32a5ab3e21f9ee532540d966d739086825ec5c34))
* 添加更多漫画语言类型 ([1781a75](https://github.com/chu-shen/BangumiKomga/commit/1781a75bce2431824217b7676f6beb633f2bf4f7))


### Bug Fixes

* 使用最新 API ([07cbf1e](https://github.com/chu-shen/BangumiKomga/commit/07cbf1ef365886813085efeb3d0b7dd31d7af8a5))
* 修复对 `IndexedDataReader` 中成员函数的无效引用 ([#69](https://github.com/chu-shen/BangumiKomga/issues/69)) ([3152d8a](https://github.com/chu-shen/BangumiKomga/commit/3152d8a0fea33f3d7cfdd5a4e440576e515c65ef))
* 修正语言代码 ([b676c0e](https://github.com/chu-shen/BangumiKomga/commit/b676c0ecae0d7354b7a71a1035d95d268623363c))
* 处理 relation_list 为 None 的情况 ([406fdfe](https://github.com/chu-shen/BangumiKomga/commit/406fdfe7b2ef1a9769a4cb6a82c0aee7ef3e1481))
* 添加 IS_NOVEL_ONLY 选项指定是否komga只包含小说数据 ([#59](https://github.com/chu-shen/BangumiKomga/issues/59)) ([71803a8](https://github.com/chu-shen/BangumiKomga/commit/71803a8540b261fd6030ac4c935ae04c2578bcf1))
* 类型注解错误 ([c628f6f](https://github.com/chu-shen/BangumiKomga/commit/c628f6f4db3bd0e1d6099c4575f9cbac41e21f51))

## [0.13.0](https://github.com/chu-shen/BangumiKomga/compare/v0.12.0...v0.13.0) (2025-04-25)


### Features

* 完善年龄限制逻辑 ([5e9af4f](https://github.com/chu-shen/BangumiKomga/commit/5e9af4f9dce50a3fc1e27804a91ceeee42463f05))
* 新增 bgm 数据源工厂 ([3a6f4c8](https://github.com/chu-shen/BangumiKomga/commit/3a6f4c8cdd9943d810510398fb8aaccac23cb1dd))
* 添加 bangumi Archive 自动更新器 ([#54](https://github.com/chu-shen/BangumiKomga/issues/54)) ([e0dff38](https://github.com/chu-shen/BangumiKomga/commit/e0dff38840869986361c6bbe8f53800d35e97f64))
* 添加 bgm 条目平台及关联的枚举类 ([4a61017](https://github.com/chu-shen/BangumiKomga/commit/4a61017fb2afc07c73896c45197a540df6ab557b))
* 添加基本的离线Archive元数据查询功能 ([#48](https://github.com/chu-shen/BangumiKomga/issues/48)) ([e176d3c](https://github.com/chu-shen/BangumiKomga/commit/e176d3ce5b812b80eb782a2a8797678765a13189))


### Bug Fixes

* 分离了 RECHECK_FAILED_SERIES 和 CREATE_FAILED_COLLECTION 选项 ([#52](https://github.com/chu-shen/BangumiKomga/issues/52)) ([9170afe](https://github.com/chu-shen/BangumiKomga/commit/9170afe70878be1dc6c789772a6a0fa0caaf72af))
* 完善缩略图逻辑 ([fa03358](https://github.com/chu-shen/BangumiKomga/commit/fa0335850b486799560c7b182ba6958b68c08b19))
* 捕获所有异常 ([d67383a](https://github.com/chu-shen/BangumiKomga/commit/d67383a2975fe6be532dc8bff0894d1a9abf9c65))


### Documentation

* 修正 cbl 和 RECHECK_FAILED_SERIES 说明 ([38a5b87](https://github.com/chu-shen/BangumiKomga/commit/38a5b87accc3895abbc6a839f34e8da337ec84fe))
* 更新「为小说添加元数据」的说明 ([88563f4](https://github.com/chu-shen/BangumiKomga/commit/88563f44356479b8cf246e5221e1ac7e3c2329a6))
* 添加配置更新警告 ([22ff4a2](https://github.com/chu-shen/BangumiKomga/commit/22ff4a2f0d74be54e3dce9d1252891870bf4cb54))

## [0.12.0](https://github.com/chu-shen/BangumiKomga/compare/v0.11.0...v0.12.0) (2025-03-29)


### Features

* 使用 FUZZ 对 bgm 搜索结果进行过滤和排序 ([b2d1962](https://github.com/chu-shen/BangumiKomga/commit/b2d19622cfb29534a26539840ad9afe3e05561df))

## [0.11.0](https://github.com/chu-shen/BangumiKomga/compare/v0.10.0...v0.11.0) (2025-03-27)


### Features

* 日志支持同时输出到文件和显示在 docker 日志窗口 ([84ac359](https://github.com/chu-shen/BangumiKomga/commit/84ac359f472b2648d13d3470e48afca784c65411)), closes [#23](https://github.com/chu-shen/BangumiKomga/issues/23)


### Bug Fixes

* 检查 cbl 获取的元数据是否为空&添加日志 ([c9ecc45](https://github.com/chu-shen/BangumiKomga/commit/c9ecc4528410064e3de1d2a998d48404a26728b9))


### Documentation

* 添加 cbl 修改图例 ([c0169ed](https://github.com/chu-shen/BangumiKomga/commit/c0169edab8f022033375d32b3b01116e6bb12700))

## [0.10.0](https://github.com/chu-shen/BangumiKomga/compare/v0.9.1...v0.10.0) (2025-03-05)


### Features

* 为存在`Bangumi`链接的系列在排序标题中添加首字母 ([9bee000](https://github.com/chu-shen/BangumiKomga/commit/9bee000666e52f6858ce3023035493666efe643d))
* 支持系列在英文字母导航中分类显示 ([7c6996d](https://github.com/chu-shen/BangumiKomga/commit/7c6996db55be10f7d3fb0d1acbaa146cf8655b74))


### Documentation

* 完善 docker 执行说明 ([602dc5d](https://github.com/chu-shen/BangumiKomga/commit/602dc5d74d5340a62003aa30bc9f5074431cf9dd))

## [0.9.1](https://github.com/chu-shen/BangumiKomga/compare/v0.9.0...v0.9.1) (2025-01-14)


### Bug Fixes

* 修正罗马数字匹配问题 ([35c8ef3](https://github.com/chu-shen/BangumiKomga/commit/35c8ef370ec2ad7aa8b0bb8fe974face95a293e8))

## [0.9.0](https://github.com/chu-shen/BangumiKomga/compare/v0.8.3...v0.9.0) (2024-12-27)


### Features

* 单册匹配时支持罗马数字 ([2c2651b](https://github.com/chu-shen/BangumiKomga/commit/2c2651b9de220b271c5c3993bd094cf1b62d0351)), closes [#26](https://github.com/chu-shen/BangumiKomga/issues/26)
* 单册支持 cbl ([96875a2](https://github.com/chu-shen/BangumiKomga/commit/96875a2b19c3203df4e5239fb2317e3222f589d6))


### Bug Fixes

* 移除同步阅读进度中的`FORCE_REFRESH_LIST`配置 ([69ff03a](https://github.com/chu-shen/BangumiKomga/commit/69ff03ae76bc39a006844e829a2a58a15cd96c88))

## [0.8.3](https://github.com/chu-shen/BangumiKomga/compare/v0.8.2...v0.8.3) (2024-10-17)


### Bug Fixes

* 修复获取序号逻辑 ([dbce1cc](https://github.com/chu-shen/BangumiKomga/commit/dbce1cca8197734b2b8def339bd15f07a3641fd4))
* 移除中文数字匹配 ([5fbbd6e](https://github.com/chu-shen/BangumiKomga/commit/5fbbd6e6c18faaeb0696463373412db8c09703e2))

## [0.8.2](https://github.com/chu-shen/BangumiKomga/compare/v0.8.1...v0.8.2) (2024-10-17)


### Bug Fixes

* 不刮削无序号单行本 ([08d47fe](https://github.com/chu-shen/BangumiKomga/commit/08d47fe42a79b2597b8f822450490d92b169a138))

## [0.8.1](https://github.com/chu-shen/BangumiKomga/compare/v0.8.0...v0.8.1) (2024-10-17)


### Documentation

* update installation guide ([0fd61e0](https://github.com/chu-shen/BangumiKomga/commit/0fd61e0b2df6f6fb7cd7f23c18cf0ae07a937997))

## [0.8.0](https://github.com/chu-shen/BangumiKomga/compare/v0.7.0...v0.8.0) (2024-10-17)


### Features

* Bangumi 匹配算法切换为 TheFuzz ([f89cd07](https://github.com/chu-shen/BangumiKomga/commit/f89cd07644946b90cab0e403d6086dcba3e69e21))
* 优化刮削逻辑，移除`FORCE_REFRESH_LIST`配置 ([c497d30](https://github.com/chu-shen/BangumiKomga/commit/c497d3076b0645166e04b7bbfd1e5573e8ed6b18))

## [0.7.0](https://github.com/chu-shen/BangumiKomga/compare/v0.6.0...v0.7.0) (2024-10-15)


### Features

* support get vol or chap number ([cba4e49](https://github.com/chu-shen/BangumiKomga/commit/cba4e495797f5e82e3f69e108740856d8a71c2e5))


### Performance Improvements

* 不再重复读取人名文件 ([f9bc723](https://github.com/chu-shen/BangumiKomga/commit/f9bc72345a3d411307b74be8b5553dfce52fd8a4))


### Documentation

* 完善 docker 说明 ([2604a9c](https://github.com/chu-shen/BangumiKomga/commit/2604a9c21b2d9313f808c6b0ada687b00d45f585))

## [0.6.0](https://github.com/chu-shen/BangumiKomga/compare/v0.5.0...v0.6.0) (2024-07-01)


### Features

* 支持更新元数据时替换单册封面 ([d31a0b7](https://github.com/chu-shen/BangumiKomga/commit/d31a0b7fa6f5e05591c2ee6082026a28b1b25684))

## [0.5.0](https://github.com/chu-shen/BangumiKomga/compare/v0.4.1...v0.5.0) (2024-06-02)


### Features

* 支持更新元数据时替换系列封面 ([02b853f](https://github.com/chu-shen/BangumiKomga/commit/02b853f88773f1e52c83f942219ba84fa310ed92))


### Bug Fixes

* 上传封面前先检测是否已有海报 ([ebc429c](https://github.com/chu-shen/BangumiKomga/commit/ebc429c8d1b4755d2fb0615be68578bbf69f803d))


### Performance Improvements

* 调整代码，改为使用 Session ([5292861](https://github.com/chu-shen/BangumiKomga/commit/529286169a6ceb4f564eb248ec706f9aba204fc5))


### Documentation

* 添加 Komga 缩略图说明 ([a4b31d7](https://github.com/chu-shen/BangumiKomga/commit/a4b31d7b7b5b70ae2cd3d24797aa394bef3ea70a))

## [0.4.1](https://github.com/chu-shen/BangumiKomga/compare/v0.4.0...v0.4.1) (2024-06-01)


### Bug Fixes

* 一次性获取 komga 所有系列 ([ee1adc0](https://github.com/chu-shen/BangumiKomga/commit/ee1adc06d410c0c677b177c286e2f2bde5bc9819))


### Documentation

* 添加 Docker 镜像示例 ([44e68ac](https://github.com/chu-shen/BangumiKomga/commit/44e68ace5d03540bc1ce5864ad792e9e23cd0891))

## 0.4.0 (2023-07-07)


### Features

* 新增komga收藏的新增、删除、搜索函数 ([d3556e5](https://github.com/chu-shen/BangumiKomga/commit/d3556e515d78f9af6aebda42cfa7e5122f4e09d8))
* 新增通知功能 ([0eddf3f](https://github.com/chu-shen/BangumiKomga/commit/0eddf3f31e6a7701e57fc703b6f2b5f665b3d584))


### Bug Fixes

* 修复收藏搜索与删除逻辑 ([fe95d98](https://github.com/chu-shen/BangumiKomga/commit/fe95d987ae3b5d339c33d3ab698ce140c73cd3a6))
* 繁转简后再执行bangumi查询 ([9af7438](https://github.com/chu-shen/BangumiKomga/commit/9af7438da192d988f1c32d3a25d84a8f35fe7483))


### Documentation

* docs:  ([6876e47](https://github.com/chu-shen/BangumiKomga/commit/6876e478a3ffcaf57c0855502fe6b625c61a5b95))
* fix ([7588b0b](https://github.com/chu-shen/BangumiKomga/commit/7588b0b695e946f7783cf345d6f3dec04085697f))
* 添加新功能说明 ([eec3c24](https://github.com/chu-shen/BangumiKomga/commit/eec3c24fd26a0def0cb5367fce71959a2a4b7be1))
* 补充收藏说明 ([dbccfab](https://github.com/chu-shen/BangumiKomga/commit/dbccfaba5636150799efe9b6a25caed9b6b0faa8))
