FROM python:3.11-slim
WORKDIR /app

# instala grpcio diretamente (sem uv, que é ferramenta de dev)
RUN pip install --no-cache-dir grpcio protobuf

# copia os stubs gerados pelo protoc e o tg_sdk
COPY sdk/python/src ./sdk/python/src

# copia o código do agente (beliefs, plans e o agente em si)
COPY agents/bdi-agent/beliefs.py .
COPY agents/bdi-agent/plans.py .
COPY agents/bdi-agent/main.py .

ENV PYTHONPATH=/app/sdk/python/src

CMD ["python", "main.py"]
