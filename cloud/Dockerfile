FROM python:3.8-slim
USER root
WORKDIR /app
COPY application.py /app
COPY model_Dhahran_Mall.sav /app
COPY model_KFUPM.sav /app
RUN apt-get update \
    && apt-get install -y gcc
RUN pip install \
        paddlepaddle\
        "paddleocr>=2.0.1"\
        pybase64\
        Pillow\
        flask\
        pymongo\
        "pymongo[srv]"\
        joblib\
        sklearn\
        numpy
RUN pip uninstall -y \
    opencv-contrib-python\
    opencv-python
RUN pip install opencv-python-headless
EXPOSE 80
ENV NAME World
CMD ["python", "application.py"]


