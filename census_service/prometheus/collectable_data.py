import prometheus_client

request_count = prometheus_client.Counter('request_counter', 'Counts number of requests accepted')
cpu_usage = prometheus_client.Gauge('cpu_usage', 'Get current cpu usage')
ram_usage = prometheus_client.Gauge('ram_usage', 'Get current ram usage')
storage_usage = prometheus_client.Gauge('storage_usage', 'Get current storage usage')

def generate_data():
    return prometheus_client.generate_latest()