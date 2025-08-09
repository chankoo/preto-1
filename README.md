# Preto-1: HR Data Analysis & Visualization

## 요구 사항

- [Docker](https://www.docker.com/get-started)


## 빌드 및 실행

1.  **Docker 이미지 빌드**

    프로젝트 루트 디렉토리에서 다음 명령어를 실행하여 Docker 이미지를 빌드드니다.

    ```sh
    docker build -t preto-1 .
    ```

2.  **Docker 컨테이너 실행**

    다음 명령어로 컨테이너를 백그라운드에서 실행합니다. streamlit과 jupyter를 위한 포트를 매핑하고, 로컬의 프로젝트 디렉토리를 컨테이너의 `/app` 디렉토리와 동기화합니다.

    ```sh
    docker run --name hra -d -p 8501:8501 -p 8888:8888 -v "$(pwd)":/app preto-1
    ```

    > **윈도우 사용자 참고 (Note for Windows Users):**
    >
    > Windows 환경에서는 `$(pwd)` 대신 현재 디렉토리를 나타내는 명령어로 변경해야 합니다. 사용하시는 셸에 맞는 아래 명령어를 사용하세요.
    >
    > - **Command Prompt (CMD):**
    >   ```cmd
    >   docker run --name hra -d -p 8501:8501 -p 8888:8888 -v "%cd%":/app preto-1
    >   ```
    >
    > - **PowerShell:**
    >   ```powershell
    >   docker run --name hra -d -p 8501:8501 -p 8888:8888 -v "${pwd}:/app" preto-1
    >   ```


## 설정
Jupyter Notebook로 작업한 결과를 streamlit으로 서빙합니다. 이를 위해 jupyter와 streamlit 프로세스를 각각 실행하는 쉘 스크립트를 작성했습니다.

```bash
[start.sh]
#!/bin/bash

# Set the PYTHONPATH to include the src directory
export PYTHONPATH="${PYTHONPATH}:/app/src"

# Start Jupyter Notebook using the config file
jupyter notebook --config=/app/jupyter_notebook_config.py &

# Start Streamlit app
streamlit run src/app.py --server.port=8501 --server.address=0.0.0.0
```

## 사용 방법

-   **Streamlit 앱 접속:**
    -   URL: [http://localhost:8501](http://localhost:8501)

-   **Jupyter Notebook 접속:**
    -   URL: [http://localhost:8888](http://localhost:8888)

-   **Notebook 변환 스크립트 실행**

    `.ipynb` 파일의 변경 사항을 `.py` 스크립트로 변환하려면, 다음 명령어를 실행합니다. `convert_notebooks.py`는 `notebooks/` 디렉토리의 노트북을 각각 `src/services/` 디렉토리로 변환하도록 설정되어 있습니다.

    ```sh
    docker exec hra python convert_notebooks.py
    ```

## 컨테이너 관리

-   **컨테이너 중지:**
    ```sh
    docker stop hra
    ```

-   **컨테이너 삭제:**
    ```sh
    docker rm hra
    ```

-   **(옵션) 컨테이너 내부 접근:**
    ```sh
    docker exec -it hra /bin/bash
    ```