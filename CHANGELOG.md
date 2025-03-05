# Changelog

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
