FROM python:3.11-slim

WORKDIR /app

# Installation de Java requis pour Kafka
RUN apt-get update && apt-get install -y \ 
    default-jdk \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY exporter.py .

RUN pip install pyspark

ENV JAVA_HOME=/usr/lib/jvm/default-java
ENV PATH="${JAVA_HOME}/bin:${PATH}"

CMD ["python", "exporter.py"]