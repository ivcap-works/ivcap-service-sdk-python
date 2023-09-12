import docker
import os

client = docker.from_env()

current_directory = os.getcwd()
print(f"{current_directory=}")

volume_binding = {
    os.path.join(current_directory, "io"): {
        'bind': '/io',
        'mode': 'rw',
    }
}

client.containers.run(
    image="clews/primitive:latest",
    volumes=volume_binding,
    command="-i /io/input/lemur.jpg -o /io/output/lemur.jpg -n 100 -m 1 -v",
    remove=True
)