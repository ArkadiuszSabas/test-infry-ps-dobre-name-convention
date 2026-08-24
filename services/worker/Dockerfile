FROM python:3.14-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PIP_ROOT_USER_ACTION=ignore \
    UV_LINK_MODE=copy

WORKDIR /workspace

RUN python -m pip install --no-cache-dir --upgrade pip uv

COPY pyproject.toml uv.lock ./
COPY services/api/pyproject.toml ./services/api/pyproject.toml
COPY services/llmmagic/pyproject.toml ./services/llmmagic/pyproject.toml
COPY packages/backend-runtime ./packages/backend-runtime
COPY packages/core ./packages/core
COPY packages/connectors ./packages/connectors
COPY packages/integrations ./packages/integrations
COPY deployments ./deployments
COPY services/worker ./services/worker

RUN uv export --locked --no-dev --package docmind-worker --no-emit-package docmind-worker --no-emit-package docmind-backend-runtime --no-emit-package docmind-core --no-emit-package docmind-connectors --no-emit-package docmind-integrations --format requirements-txt -o /wheels/requirements.txt > /dev/null
RUN uv build packages/backend-runtime --out-dir /wheels
RUN uv build packages/core --out-dir /wheels
RUN uv build packages/connectors --out-dir /wheels
RUN uv build packages/integrations --out-dir /wheels
RUN uv build services/worker --out-dir /wheels

FROM python:3.14-slim AS runtime

ENV PIP_ROOT_USER_ACTION=ignore \
    PYTHONUNBUFFERED=1

RUN addgroup --system docmind \
    && adduser --system --ingroup docmind docmind \
    && python -m pip install --no-cache-dir --upgrade pip

COPY --from=builder /wheels /wheels
COPY --from=builder /workspace/deployments /app/deployments
RUN python -m pip install --no-cache-dir -r /wheels/requirements.txt
RUN python -m pip install --no-cache-dir --no-deps /wheels/docmind_backend_runtime*.whl /wheels/docmind_core*.whl /wheels/docmind_integrations*.whl /wheels/docmind_connectors*.whl /wheels/docmind_worker*.whl \
    && rm -rf /wheels

USER docmind
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "docmind_worker.main:app", "--host", "0.0.0.0", "--port", "8000"]
