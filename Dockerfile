FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Inside a container the server must listen on all interfaces; the host port
# mapping below keeps it reachable only from your own machine.
ENV SPEKTRA_HOST=0.0.0.0 SPEKTRA_WORKSPACE=/app/workspace
EXPOSE 5000
CMD ["python", "app.py"]
