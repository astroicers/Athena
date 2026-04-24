FROM athena-mcp-base:latest

# Install xfreerdp3 for RDP auth-only checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    freerdp3-x11 && \
    rm -rf /var/lib/apt/lists/*

# Enable OpenSSL 3 legacy provider for pywinrm NTLM (MD4 hash needed for NTLMv2)
RUN printf '%s\n' \
    'openssl_conf = openssl_init' \
    '[openssl_init]' \
    'providers = provider_sect' \
    '[provider_sect]' \
    'default = default_sect' \
    'legacy = legacy_sect' \
    '[default_sect]' \
    'activate = 1' \
    '[legacy_sect]' \
    'activate = 1' \
    > /etc/ssl/openssl-legacy.cnf
ENV OPENSSL_CONF=/etc/ssl/openssl-legacy.cnf

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

CMD ["python", "-m", "server"]
