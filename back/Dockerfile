# syntax=docker/dockerfile:1
# Build context: back/ (run from the repository root: docker build -t port8282-back:local ./back)
# Verified multi-platform Temurin 21.0.13+9 images; update digests deliberately.
FROM eclipse-temurin:21-jdk-jammy@sha256:4b1a74fbffbe6b4e7b6f0171a472478282fb463790a51edf10e465d578f22b69 AS build
WORKDIR /workspace

COPY --chmod=755 gradlew ./gradlew
COPY gradle/ ./gradle/
COPY build.gradle settings.gradle gradle.properties gradle.lockfile ./
COPY src/ ./src/

# The Wrapper downloads Gradle; build includes the HTTP health test and strict dependency locks.
RUN --mount=type=cache,id=port8282-back-gradle,target=/root/.gradle,sharing=locked \
    ./gradlew --no-daemon build \
    && mkdir /out \
    && test "$(find build/libs -maxdepth 1 -type f -name '*.jar' ! -name '*-plain.jar' | wc -l)" -eq 1 \
    && find build/libs -maxdepth 1 -type f -name '*.jar' ! -name '*-plain.jar' -exec cp {} /out/app.jar \;

# Compose development target: editable source + JDK/Gradle for tests and bootRun.
# Compose Watch syncs src/ then restarts bootRun to recompile changed Java code.
FROM eclipse-temurin:21-jdk-jammy@sha256:4b1a74fbffbe6b4e7b6f0171a472478282fb463790a51edf10e465d578f22b69 AS development
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home --shell /usr/sbin/nologin app \
    && mkdir -p /workspace /home/app/.gradle \
    && chown -R 10001:10001 /workspace /home/app
WORKDIR /workspace
ENV GRADLE_USER_HOME=/home/app/.gradle \
    SERVER_PORT=8080
COPY --chown=10001:10001 --chmod=755 gradlew ./gradlew
COPY --chown=10001:10001 gradle/ ./gradle/
COPY --chown=10001:10001 build.gradle settings.gradle gradle.properties gradle.lockfile ./
COPY --chown=10001:10001 src/ ./src/
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=5s --start-period=120s --retries=6 \
    CMD curl --fail --silent --show-error --max-time 3 "http://127.0.0.1:${SERVER_PORT}/actuator/health" > /dev/null || exit 1
CMD ["./gradlew", "--no-daemon", "bootRun"]

FROM eclipse-temurin:21-jre-jammy@sha256:1eac8b8fee11ca7d6725a48bc5d41992ed1561504ebae25490d2d062847e8269 AS runtime
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app
WORKDIR /app
COPY --from=build --chown=10001:10001 /out/app.jar ./app.jar

ENV SERVER_PORT=8080
USER 10001:10001
EXPOSE 8080
# Local profile checks the process; compose profile additionally checks its JDBC database.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl --fail --silent --show-error --max-time 3 "http://127.0.0.1:${SERVER_PORT}/actuator/health" > /dev/null || exit 1
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
