import json
import time
import uuid
from enum import Enum

class JobStatus(str, Enum):
    QUEUED = 'queued'
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILED = 'failed'

class Job:
    def __init__(self, func_string, args=None, kwargs=None, jid=None, status=JobStatus.QUEUED, retries=0, max_retries=0, enqueued_at=None, result=None, error=None):
        self.jid = jid or str(uuid.uuid4())
        self.func_string = func_string
        self.args = tuple(args) if args is not None else ()
        self.kwargs = kwargs or {}
        self.status = JobStatus(status) if isinstance(status, str) else status
        self.retries = retries
        self.max_retries = max_retries
        self.enqueued_at = enqueued_at or time.time()
        self.result = result
        self.error = error

    def to_dict(self):
        return {
            'jid': self.jid,
            'func_string': self.func_string,
            'args': self.args,
            'kwargs': self.kwargs,
            'status': self.status.value,
            'retries': self.retries,
            'max_retries': self.max_retries,
            'enqueued_at': self.enqueued_at,
            'result': self.result,
            'error': self.error,
        }

def serialize_job(job):
    return json.dumps(job.to_dict())

def deserialize_job(job_string):
    data = json.loads(job_string)
    return Job(**data)
