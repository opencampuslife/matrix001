FROM golang:1.26-alpine AS build
WORKDIR /src
COPY control-plane/go.mod control-plane/go.sum* ./
RUN go mod download 2>/dev/null || true
COPY control-plane/ ./
RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /gaokao-gateway ./cmd/gaokao-gateway

FROM alpine:3.20
RUN addgroup -S gaokao && adduser -S gaokao -G gaokao
COPY --from=build /gaokao-gateway /usr/local/bin/gaokao-gateway
COPY contracts/routes.yaml /app/contracts/routes.yaml
RUN chown -R gaokao:gaokao /app
USER gaokao
ENV ROUTES_CONTRACT_PATH=/app/contracts/routes.yaml
ENV LISTEN_ADDR=:8788
ENV SHADOW_MODE=true
ENV SHADOW_PROXY_ENABLED=false
ENV PYTHON_GATEWAY_BASE_URL=http://host.docker.internal:8787
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q -O - http://localhost:8788/api/health || exit 1
ENTRYPOINT ["/usr/local/bin/gaokao-gateway"]
