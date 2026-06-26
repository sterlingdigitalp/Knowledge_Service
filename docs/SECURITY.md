# Security — Boundaries, Credentials, and Access Control

## Purpose

This document defines the security architecture for Knowledge_Service. It specifies authentication boundaries, credential isolation, secret management, API security, and audit capabilities.

## Scope

This document covers:
- Authentication model and boundary enforcement
- Provider credential isolation
- Secret management philosophy and implementation
- API security controls
- Audit logging requirements
- Data protection in transit and at rest
- Security threat model

## Design Rationale

Security is designed around Principle 13 (Security Through Isolation). The primary security mechanism is architectural separation: provider credentials are isolated from application code, authentication boundaries are enforced at the API Layer, and all access is auditable.

The security model assumes:
- The network between applications and Knowledge_Service is untrusted
- Provider systems may have different security postures
- Applications may be compromised; provider credentials must remain protected
- Internal components may have bugs; credential exposure must be minimized

## Authentication Model

### Application Authentication

Applications authenticate to Knowledge_Service using API keys.

**Mechanism**: Bearer token in `Authorization` header:
```
Authorization: Bearer <api_key>
```

**Validation**:
1. API key is looked up in the authentication store
2. Key status is verified (active, not revoked, not expired)
3. Request scope is checked against key permissions
4. Rate limit quota is verified
5. Request proceeds only if all checks pass

**Key Storage**:
- API keys are hashed using a slow hash function (e.g., bcrypt, argon2) before storage
- The plaintext key is never stored; it is returned to the administrator only at creation time
- Key rotation replaces the old hash with a new one while the old key remains valid during transition

### Provider Authentication

Knowledge_Service authenticates to providers using provider credentials.

**Mechanism**: Credentials are injected into the Provider Layer at initialization time. They are never exposed to:
- The API Layer
- The Planning Layer
- The Acquisition Layer (beyond what is necessary for the provider call)
- Application code
- Logs or observability data

**Credential Types by Provider**:
| Provider Type | Credential Type | Storage Location |
|--------------|----------------|-----------------|
| Crawler (Crawl4AI) | None (public) | N/A |
| Search (SearXNG) | Instance URL, optional API key | Provider Layer config store |
| GitHub | Personal access token or OAuth token | Provider Layer config store |
| RSS | None (public feeds) | N/A |
| PDF Processor | Service credentials | Provider Layer config store |
| Database | Connection string with auth | Provider Layer config store |

### Cross-Layer Authentication Boundary

```
Untrusted Network → [API Layer: Authenticate Application] → Trusted Internal Network
                                                              ↓
                                                      Internal layers communicate
                                                      without per-request auth
                                                      (trusting the network boundary)
                                                              ↓
                                                      [Provider Layer: Authenticate to Providers]
                                                              ↓
                                                    External Provider Networks
```

The API Layer is the security perimeter. Everything inside the trusted network boundary communicates freely; everything outside must authenticate through the API Layer.

## Credential Isolation

### Isolation Principle

Provider credentials exist ONLY within the Provider Layer. No other layer has access to them.

**Enforcement mechanisms**:
1. **Code structure**: Provider credentials are stored in provider-specific configuration objects that are only accessible within provider implementation files
2. **Interface contracts**: The Provider Interface does not expose credential fields; it accepts pre-configured provider instances
3. **Logging redaction**: Any log output containing credential-like strings is automatically redacted
4. **Memory security**: Credentials are cleared from memory after use where the programming language supports it

### Credential Injection Flow

```
Configuration (encrypted at rest)
    ↓
Secret Manager (runtime decryption)
    ↓
Provider Layer initialization (credentials injected into provider instances)
    ↓
Provider uses credentials for external calls
    ↓
Credentials never leave Provider Layer scope
```

### Secret Manager Integration

Secrets are managed by a dedicated secret manager service:
- **AWS Secrets Manager** / **HashiCorp Vault** / **Azure Key Vault** (implementation-specific)
- Secrets are fetched at runtime, not embedded in configuration files
- Configuration files reference secrets by identifier, not by value
- Secret rotation is handled by the secret manager; Knowledge_Service fetches fresh values on provider re-initialization

## API Security Controls

### Rate Limiting

Rate limits prevent abuse and protect downstream providers from overload.

| Control | Scope | Default | Configurable |
|---------|-------|---------|-------------|
| Requests per minute | Per API key | Defined in configuration | Yes |
| Burst size | Per API key | 2× rate limit | Yes |
| Global rate limit | All keys combined | Defined in configuration | Yes |

Rate limit violations return HTTP 429 with `Retry-After` header.

### Request Validation

All requests are validated before processing:
1. **Schema validation**: Request body matches the expected JSON schema for the endpoint
2. **Size limits**: Maximum request body size enforced (default: 1 MB)
3. **Field constraints**: Enum values, date formats, URI formats validated
4. **SQL injection prevention**: Query parameters sanitized; no raw SQL construction from user input
5. **Path traversal prevention**: File paths and URLs validated against allowed patterns

### Input Sanitization

Content received from providers is treated as untrusted input:
- HTML content is cleaned before storage (script tags, event handlers removed)
- Markdown output is validated for safe rendering
- Binary content is checked for malicious file signatures
- File uploads (if supported) are scanned for malware

### TLS Requirements

- All external communication uses HTTPS/TLS 1.2 or higher
- TLS certificates must be valid and not expired
- Certificate pinning is optional but recommended for high-security deployments
- Internal service-to-service communication may use mTLS in production deployments

## Audit Logging

### Auditable Events

The following events are logged for audit purposes:

| Event | Data Logged | Retention |
|-------|------------|-----------|
| API key created/rotated/revoked | Key ID, creator, timestamp, action | Indefinite |
| Application authenticated successfully | API key ID (hashed), IP address, timestamp | 90 days |
| Authentication failure | API key ID (if valid), IP address, reason, timestamp | 90 days |
| Provider credential accessed | Provider name, accessing component, timestamp | 90 days |
| Source registry modified | Source ID, change type, modifier, timestamp | Indefinite |
| Knowledge object deleted | Object ID, deleting entity, reason, timestamp | Indefinite |
| Configuration changed | Configuration key, old value (redacted), new value (redacted), changer, timestamp | 90 days |

### Audit Log Properties

- **Append-only**: Audit entries are never modified or deleted (except for compliance-driven deletion after retention period)
- **Tamper-evident**: Audit log integrity is verifiable (cryptographic chaining or WORM storage)
- **Separate storage**: Audit logs are stored separately from operational logs to prevent tampering through log manipulation
- **Access controlled**: Only authorized administrators can read audit logs

### What Is NOT Logged

The following are explicitly excluded from audit logs:
- Provider credentials or API key values (even hashed)
- Full request/response bodies (only metadata is logged)
- Knowledge object content (only identifiers and access events are logged)
- Internal error stack traces in production

## Data Protection

### In Transit

| Communication Path | Encryption | Protocol |
|-------------------|-----------|----------|
| Application → Knowledge_Service | Required | HTTPS/TLS 1.2+ |
| Knowledge_Service → Providers | Recommended | HTTPS/TLS where provider supports it |
| Internal layer communication | Deployment-dependent | mTLS in production; plaintext in single-process development |

### At Rest

| Data Type | Encryption | Key Management |
|-----------|-----------|---------------|
| Knowledge objects (primary store) | Recommended (database-level) | Database encryption keys managed by infrastructure |
| Vector embeddings | Recommended | Same as primary store |
| Audit logs | Required | Separate key from application data |
| Configuration files | N/A (secrets not stored in config files) | N/A |
| Cache data | Optional (transient, TTL-bound) | Same as storage backend |

### Data Classification

| Class | Examples | Protection Level |
|-------|----------|-----------------|
| Public | Health check endpoint, API documentation | Standard web security |
| Internal | Knowledge objects, source registry | Authentication required; audit logged |
| Confidential | Provider credentials, API keys | Isolated in Provider Layer; encrypted at rest; never logged |
| Restricted | Audit logs, secret manager access | Separate storage; limited access; tamper-evident |

## Security Threat Model

### Threats and Mitigations

| Threat | Likelihood | Impact | Mitigation |
|--------|-----------|--------|------------|
| Unauthorized API access | Medium | High | API key authentication; scope-based authorization; rate limiting |
| Provider credential theft | Low | Critical | Credential isolation in Provider Layer; encrypted storage; no logging of credentials |
| Provider compromise (malicious provider) | Low | Medium | Input validation; content sanitization; provider health monitoring |
| Data exfiltration via knowledge objects | Low | High | Access controls on retrieval endpoints; audit logging of all access |
| Denial of service via resource exhaustion | Medium | Medium | Rate limiting; request size limits; circuit breakers on providers |
| Supply chain attack (provider SDK compromise) | Low | Critical | Dependency scanning; pinned dependency versions; minimal provider SDK surface area |
| Configuration leakage | Low | High | Secrets in secret manager; no credentials in config files committed to VCS |

### Assumptions About External Systems

- Provider systems may have their own security vulnerabilities; Knowledge_Service mitigates by treating provider responses as untrusted input
- Provider APIs may change authentication mechanisms; the Provider Layer abstracts these changes
- Network infrastructure between Knowledge_Service and providers may be intercepted; TLS is required for all external communication

## Configuration Security

### Sensitive Configuration

The following configuration values must never be committed to version control:
- Provider API keys and tokens
- Database connection strings with credentials
- Secret manager access keys
- TLS private keys

### Secure Configuration Pattern

```yaml
# Configuration file (committed to VCS - NO secrets)
providers:
  github:
    enabled: true
    endpoint: "https://api.github.com"
    credentials_ref: "vault:secret/data/providers/github"  # Reference only

# Secret manager stores the actual values
# vault:secret/data/providers/github → { "token": "ghp_xxxxxx" }
```

### Environment Variables

Environment variables may be used for configuration but should not contain secrets in shared or CI/CD environments. Secrets should come from the secret manager, not environment variables, except in development environments where convenience outweighs risk.

## Security Updates and Vulnerability Management

### Dependency Scanning

- All provider SDK dependencies are scanned for known vulnerabilities
- Scanning occurs on every dependency update and periodically (weekly)
- Critical vulnerabilities trigger immediate patching; moderate vulnerabilities are scheduled

### Security Patch Policy

| Severity | Response Time | Deployment Window |
|----------|--------------|-------------------|
| Critical (RCE, auth bypass) | 24 hours | Emergency deployment |
| High (auth weakness, data exposure) | 72 hours | Next scheduled release |
| Medium (informational disclosure) | 1 week | Regular release cycle |
| Low (cosmetic, minor) | Best effort | Regular release cycle |

## Assumptions

- A secret manager service is available in the deployment environment
- TLS certificates are managed by infrastructure (not manually)
- Network segmentation separates Knowledge_Service from provider networks appropriately
- Application developers follow secure coding practices for their own code

## Tradeoffs

### Per-Request vs. Connection-Level Authentication

**Decision**: Authenticate each API request individually.

**Rationale**: Applications may share network connections (connection pooling). Authenticating per-request ensures that even if a connection is reused across different application contexts, authentication is verified for each request. The tradeoff is additional validation overhead per request, which is negligible compared to acquisition and processing costs.

### mTLS for Internal Communication

**Decision**: mTLS is optional for internal layer communication, required only in production deployments with distributed layers.

**Rationale**: In single-process deployments (development), mTLS adds unnecessary complexity. In distributed deployments, mTLS provides defense-in-depth but requires certificate management overhead. The decision to enable mTLS internally is deployment-specific.

### Audit Log Retention

**Decision**: 90 days for operational audit logs; indefinite for security-critical events (key management, source registry changes).

**Rationale**: Full retention of all audit data creates storage and privacy burdens. Security-critical events are retained indefinitely because they may be needed for forensic investigation months or years later. Operational events have a shorter relevance window.

## Future Evolution

Future phases may add:
- OAuth 2.0 / OIDC integration for application authentication (replacing or supplementing API keys)
- Role-based access control (RBAC) for finer-grained permission management
- Tenant isolation for multi-tenant deployments
- Data loss prevention (DLP) scanning on knowledge objects leaving the system
- Automated security testing in CI/CD pipeline

All additions must maintain the credential isolation principle and audit logging requirements defined in this document.
