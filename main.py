from fastapi import FastAPI, Request, Response
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry import trace
from datetime import datetime
from census_service.prometheus.collectable_data import request_count, generate_data, cpu_usage, ram_usage, storage_usage
import psutil
import json

def lifespan(app):
    yield

app = FastAPI(lifespan=lifespan)

# instrument fastapi for opentelemetry
FastAPIInstrumentor.instrument_app(app)

@app.middleware('http')
async def request_response_middleware(request:Request, call_next):
    request_count.inc()
    otl_tracer = trace.get_tracer(__name__)
    with otl_tracer.start_as_current_span(f'[{request.method}] {request.url.__str__()}') as tracer:
        tracer.set_attribute('http.start_time', datetime.now().strftime('%d/%m/%Y, %H:%M:%S, %Z'))
        tracer.set_attribute('http.url', request.url)
        tracer.set_attribute('http.query_params', json.dumps(dict(request.query_params)))
        tracer.set_attribute('http.headers', json.dumps(dict(request.headers)))
        if request.method.lower() != 'get':
            body = await request.body()
            tracer.set_attribute('http.body', json.dumps(body.decode('utf-8')))

        start_time = datetime.now()
        
        response = await call_next(request)

        duration_in_seconds = (datetime.now() - start_time).microseconds * 0.001

        response_body = b""

        async for chunk in response.body_iterator:
            response_body += chunk
        
        tracer.set_attribute('http.response_status_code', response.status_code)
        tracer.set_attribute('http.response_headers', json.dumps(dict(response.headers)))
        tracer.set_attribute('http.response_body', json.dumps(response_body.decode('utf-8')))
        tracer.set_attribute('http.duration_in_sec', duration_in_seconds)

        return Response(
            content=response_body, 
            status_code=response.status_code, 
            headers=dict(response.headers)
            )
    

# set up scrape endpoint for prometheus   
@app.get('/metrics')
def metrics():
    cpu_usage.set(psutil.cpu_percent())
    ram_usage.set(psutil.virtual_memory().percent)
    storage_usage.set(psutil.disk_usage('/').percent)

    return Response(
        content= generate_data(), 
        status_code=200, 
        media_type='text/plain')