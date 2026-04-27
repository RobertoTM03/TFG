FROM postgres:16 AS builder

RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    libssl-dev \
    pkg-config \
    jq \
    postgresql-server-dev-16 \
    && rm -rf /var/lib/apt/lists/*

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

RUN cd /tmp && \
    git clone --branch v0.8.0 https://github.com/pgvector/pgvector.git && \
    cd pgvector && \
    make && \
    make install

RUN cd /tmp && \
    git clone --branch 0.9.0 https://github.com/timescale/pgvectorscale.git && \
    cd pgvectorscale/pgvectorscale && \
    cargo install --locked cargo-pgrx --version $(cargo metadata --format-version 1 | jq -r '.packages[] | select(.name == "pgrx") | .version') && \
    cargo pgrx init --pg16 $(which pg_config) && \
    cargo pgrx install --release

FROM postgres:16

COPY --from=builder /usr/share/postgresql/16/extension/vector--*.sql    /usr/share/postgresql/16/extension/
COPY --from=builder /usr/share/postgresql/16/extension/vector.control    /usr/share/postgresql/16/extension/
COPY --from=builder /usr/lib/postgresql/16/lib/vector.so                 /usr/lib/postgresql/16/lib/

COPY --from=builder /usr/share/postgresql/16/extension/vectorscale--*.sql /usr/share/postgresql/16/extension/
COPY --from=builder /usr/share/postgresql/16/extension/vectorscale.control /usr/share/postgresql/16/extension/
COPY --from=builder /usr/lib/postgresql/16/lib/vectorscale*.so             /usr/lib/postgresql/16/lib/
