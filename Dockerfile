FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    lua5.1 \
    liblua5.1-dev \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/viruscamp/luadec.git /luadec \
    && cd /luadec/lua-5.1 && make linux \
    && cd /luadec && make LUA_VERSION=5.1 \
    && cp /luadec/luadec /usr/local/bin/luadec

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
