# sitewitness for bsandova.com: index built at image build from this checkout, served by uvicorn.
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /site
# texts and data files the agent reads, plus the config
COPY sitewitness.toml ./
COPY texts ./texts
COPY surf/data.json ./surf/data.json
COPY weather/data.json ./weather/data.json
COPY watch/data.json ./watch/data.json
COPY assets/detector/detector.json ./assets/detector/detector.json
COPY assets/parking2/eea_cz.json ./assets/parking2/eea_cz.json
COPY assets/cutover/report-2.json ./assets/cutover/report-2.json
COPY assets/library.json ./assets/library.json
COPY status/jobs.json ./status/jobs.json
COPY changelog/data.json ./changelog/data.json
COPY ask/eval.json ./ask/eval.json
COPY deploy/sitewitness-0.1.0-py3-none-any.whl /tmp/
RUN uv pip install --system --no-cache "sitewitness[embed] @ file:///tmp/sitewitness-0.1.0-py3-none-any.whl" && \
    python -c "import sentence_transformers; sentence_transformers.SentenceTransformer('all-MiniLM-L6-v2')" && \
    sitewitness index --embed
RUN mkdir -p /data
EXPOSE 8000
CMD ["sitewitness", "serve", "--host", "0.0.0.0", "--port", "8000"]
