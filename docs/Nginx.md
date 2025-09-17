# SSE 事件服务搭配 Nginx

推荐在 LAN 环境中连接 Komga 实例。若以 SSE 事件服务方式启动`BANGUMI KOMGA`，并且出于安全考虑将 Komga 置于 Nginx 后端, 需更改 Nginx 配置来支持 SSE 长连接。

在[该issue中](https://github.com/gotson/komga/issues/2012#issuecomment-3143750732)发现`HTTP 1.1`会触发浏览器的SSE连接数限制, 请务必在server块中至少使用 `HTTP 2`, `HTTP 2`要求`HTTPS`

以下为`nginx.conf`的`server`(以监听443端口为例)和`location`块配置参考:

```conf
  server {
    listen                443 ssl http2;
    access_log            /var/log/nginx/komga.access.log;
    error_log             /var/log/nginx/komga.error.log;
    server_name           komga.example.com;
    ssl_certificate       /SSL/komga.example.com.fullchain;
    ssl_certificate_key   /SSL/komga.example.com.key;
    ......
  }
  location / {
    # KOMGA实例地址
    proxy_pass http://komga_backend;
    # 关闭URL自动调整功能。
    proxy_redirect off;
    # 将客户端请求的 Host 头传递给后端服务器，而非使用 Nginx 代理的虚拟主机配置。
    proxy_set_header Host $http_host;
    # 传递客户端请求的原始协议（http 或 https），帮助后端处理 SSL 终止
    proxy_set_header X-Forwarded-Proto $scheme;
    # 显式指定 HTTP/1.1 协议以便支持长连接
    proxy_http_version 1.1;
    # proxy_set_header Upgrade $http_upgrade;
    # 关闭 Nginx 缓冲，实时转发后端数据到客户端，避免延迟。
    proxy_buffering off;
    # 禁用缓存，确保每次请求SSE返回最新数据
    proxy_cache off;
    # 禁用 Nginx 自动添加的 Connection: keep-alive 头，避免后端服务器提前关闭长连接。
    proxy_set_header Connection '';
    # 强制客户端或中间代理不缓存请求结果
    proxy_set_header Cache-Control 'no-cache';
    # 禁用分块传输编码，确保后端直接控制数据流
    # 后端应正确设置 Content-Type: text/event-stream
    chunked_transfer_encoding off;
    ......
 }
```
