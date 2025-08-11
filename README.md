# Crypto Exchange VPN Proxy

Уніфікований VPN проксі сервер для обходу IP блокувань криптобірж. Оптимізований для AWS t2.micro з підтримкою асинхронних запитів.

## Особливості

- ✅ **Уніфікований інтерфейс** - один POST endpoint для всіх запитів
- ✅ **Обхід IP блокувань** - проксі запити через сервер в іншому регіоні
- ✅ **Асинхронна обробка** - підтримка одночасних запитів
- ✅ **Оптимізація для t2.micro** - ресурси та налаштування під AWS
- ✅ **Rate Limiting** - автоматичне обмеження частоти запитів
- ✅ **Retry Logic** - автоматичні повторні спроби при помилках
- ✅ **HTTP протокол** - простий налаштування без SSL сертифікатів
- ✅ **Підтримка всіх HTTP методів** - GET, POST, PUT, DELETE
- ✅ **Гнучкість** - підтримка параметрів, заголовків, JSON та form data

## Оптимізація для t2.micro AWS

### Ресурси t2.micro:
- **CPU**: 1 vCPU (0.5-1.0 CPU credits)
- **RAM**: 1 GB
- **Network**: Обмежена пропускна здатність

### Налаштування:
- **Воркери**: 2 (максимум для t2.micro)
- **Конкурентні запити**: 10 одночасно
- **Rate Limiting**: 50 запитів/секунду
- **Memory limits**: 512MB для FastAPI, 128MB для nginx
- **CPU limits**: 0.5 CPU для FastAPI, 0.25 CPU для nginx

## Швидкий старт

### 1. Клонування та налаштування

```bash
git clone <your-repo>
cd vpn_proxy
```

### 2. Запуск з Docker Compose

```bash
docker-compose up -d
```

### 3. Перевірка роботи

```bash
curl http://your-domain.com/
# Повинно повернути: {"status": "healthy", "service": "Crypto Exchange VPN Proxy"}
```

### 4. Тест продуктивності

```bash
python test_async.py
```

## API Endpoints

### Health Check
```bash
GET /
```

### Уніфікований проксі endpoint
```bash
POST /proxy
```

### Статус сервера
```bash
GET /status
```

## Приклади використання

### GET запит до Binance
```bash
curl -X POST "http://your-domain.com/proxy" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://api.binance.com/api/v3/ticker/24hr",
    "method": "GET"
  }'
```

### POST запит з параметрами до Bybit
```bash
curl -X POST "http://your-domain.com/proxy" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://api.bybit.com/v5/market/tickers",
    "method": "GET",
    "params": {
      "category": "spot"
    }
  }'
```

### POST запит з JSON даними
```bash
curl -X POST "http://your-domain.com/proxy" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://api.binance.com/api/v3/order",
    "method": "POST",
    "headers": {
      "X-MBX-APIKEY": "your-api-key"
    },
    "json_data": {
      "symbol": "BTCUSDT",
      "side": "BUY",
      "type": "MARKET",
      "quantity": "0.001"
    }
  }'
```

### POST запит з form data
```bash
curl -X POST "http://your-domain.com/proxy" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://api.exchange.com/api/v1/order",
    "method": "POST",
    "data": "symbol=BTCUSDT&side=buy&quantity=0.001"
  }'
```

## Структура запиту

```json
{
  "url": "https://api.exchange.com/endpoint",
  "method": "GET|POST|PUT|DELETE",
  "params": {
    "param1": "value1",
    "param2": "value2"
  },
  "headers": {
    "Authorization": "Bearer token",
    "X-API-Key": "your-api-key"
  },
  "data": "form-data-string",
  "json_data": {
    "key": "value"
  }
}
```

### Поля запиту:

- **url** (обов'язкове): Повна URL адреса для запиту
- **method** (опціональне): HTTP метод (GET, POST, PUT, DELETE), за замовчуванням GET
- **params** (опціональне): Query параметри
- **headers** (опціональне): HTTP заголовки
- **data** (опціональне): Form data або raw data
- **json_data** (опціональне): JSON дані для POST/PUT запитів

## Інтеграція з вашим проектом

### Модифікація exchange класів

Додайте проксі URL до ваших exchange класів:

```python
import requests
import json

class Binance(Exchange):
    def __init__(self, api_key: str = None, api_secret: str = None):
        super().__init__(api_key, api_secret)
        self.proxy_url = os.getenv("PROXY_URL", "http://your-domain.com/proxy")
    
    def _make_proxy_request(self, url: str, method: str = "GET", params: dict = None, 
                           headers: dict = None, data: any = None, json_data: dict = None):
        """Make request through proxy"""
        payload = {
            "url": url,
            "method": method
        }
        
        if params:
            payload["params"] = params
        if headers:
            payload["headers"] = headers
        if data:
            payload["data"] = data
        if json_data:
            payload["json_data"] = json_data
            
        response = requests.post(self.proxy_url, json=payload)
        return response.json()
    
    async def get_spot_pairs(self):
        result = self._make_proxy_request(
            url="https://api.binance.com/api/v3/ticker/24hr",
            method="GET"
        )
        # Process result...
        return result
```

### Використання змінних середовища

```bash
export PROXY_URL="http://your-domain.com/proxy"
```

## Налаштування

### Змінні середовища

```bash
PROXY_TIMEOUT=30.0          # Таймаут запитів (секунди)
MAX_RETRIES=3               # Максимальна кількість повторних спроб
RATE_LIMIT_DELAY=0.05       # Затримка між запитами (секунди) - оптимізовано для t2.micro
MAX_CONCURRENT_REQUESTS=10   # Максимум одночасних запитів
```

### Rate Limiting

- **Всі запити**: 50 запитів/секунду (оптимізовано для t2.micro)
- **Burst**: 25 запитів

### Ресурси для t2.micro

- **FastAPI контейнер**: 512MB RAM, 0.5 CPU
- **Nginx контейнер**: 128MB RAM, 0.25 CPU
- **Воркери**: 2 (максимум для t2.micro)

## Розгортання

### Локальне тестування

```bash
python main.py
```

### Docker

```bash
# Збірка та запуск
docker-compose up -d --build

# Перегляд логів
docker-compose logs -f vpn-proxy

# Зупинка
docker-compose down
```

### AWS t2.micro розгортання

1. **Створіть EC2 інстанс** t2.micro
2. **Встановіть Docker** та Docker Compose
3. **Скопіюйте файли** проекту
4. **Запустіть** `docker-compose up -d`
5. **Налаштуйте Security Group** (порт 80)
6. **Додайте моніторинг** (CloudWatch)

### Продакшен розгортання

1. **Налаштуйте домен** (опціонально)
2. **Змініть nginx.conf** для вашого домену (якщо потрібно)
3. **Додайте моніторинг** (CloudWatch)
4. **Налаштуйте брандмауер** (Security Groups)
5. **Додайте логування** (CloudWatch Logs)

## Безпека

- ✅ Rate limiting
- ✅ Security headers
- ✅ Non-root user в Docker
- ✅ Health checks
- ✅ Input validation
- ✅ Resource limits

## Моніторинг

### Health Check
```bash
curl http://your-domain.com/status
```

### Логи
```bash
docker-compose logs -f vpn-proxy
```

### Метрики
- Кількість запитів
- Час відповіді
- Помилки
- Rate limiting events
- Active requests
- Memory usage

## Тестування продуктивності

### Запуск тестів
```bash
python test_async.py
```

### Очікувані результати для t2.micro:
- **Одночасні запити**: 10
- **Запитів/секунду**: 50
- **Середній час відповіді**: 1-3 секунди
- **Memory usage**: < 512MB

## Підтримувані біржі

- Binance
- Bybit
- OKX
- HTX (Huobi)
- KuCoin
- MEXC
- Gate.io
- WhiteBit
- LBank
- BingX
- Coinbase
- Bitget
- BitMart
- Crypto.com
- Bitfinex
- Exmo
- XT
- Gemini
- CEX.IO
- Bitstamp
- CoinDCX
- DeepCoin
- AscendEX
- Biconomy
- Weex
- Probit
- CoinW
- UZX
- Toobit
- Digifinex
- P2B
- FameEx
- IndoEx
- Pionex
- CoinLocally
- Koinbay
- ZKE
- Hotcoin
- ZED
- Bitunix
- Arkham
- OrangeX
- Bithumb
- Upbit
- Azbit
- BTCC

## Troubleshooting

### Помилка підключення
```bash
# Перевірте порти
netstat -tulpn | grep :80
```

### Rate limiting
```bash
# Перевірте логи nginx
docker-compose logs nginx
```

### Перевірка роботи проксі
```bash
# Тестовий запит
curl -X POST "http://localhost/proxy" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://httpbin.org/get",
    "method": "GET"
  }'
```

### Перевірка ресурсів
```bash
# Перевірте використання CPU та RAM
docker stats
```

## Ліцензія

MIT License 