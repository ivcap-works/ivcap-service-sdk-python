# ivcap-service: A python library for building services for the IVCAP platform

<a href="https://scan.coverity.com/projects/ivcap-service-sdk-python">
  <img alt="Coverity Scan Build Status"
       src="https://scan.coverity.com/projects/31773/badge.svg"/>
</a>

A python library containing various helper and environment functions
to simplify developing services to be deployed on IVCAP.

> **Note:** A template git repository using this library can be found on github
[ivcap-works/ivcap-python-ai-tool-template](https://github.com/ivcap-works/ivcap-python-ai-tool-template). You may clone that and start from there.

## Describe the service <a name="register"></a>

```python
logging_init()
logger = getLogger("app")

service = Service(
    name="Some service",
    contact={
        "name": "Mary Doe",
        "email": "mary.doe@acme.au",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/license/MIT",
    },
)
```


```python
class Request(BaseModel):
    jschema: str = Field("urn:sd:schema:some_tool.request.1", alias="$schema")
    ...

class Result(BaseModel):
    jschema: str = Field("urn:sd:schema:some_tool.1", alias="$schema")
    ...

def some_service(req: Request) -> Result:
    """
    Here should go a quite extensive description of what the service can be
    used for so that an agent can work out if this service is useful in
    a specific context.

    DO NOT ADD PARAMTER AND RETURN DECRIPTIONS -
       DESCRIBE THEM IN THE `Request` MODEL
    """
    ...

    return Result(...)
```

## Start the Service <a name="start"></a>

```python
if __name__ == "__main__":
    from ivcap_service import start_batch_service
    some_service(service, consume_compute)
```
