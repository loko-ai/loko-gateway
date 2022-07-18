FROM python:3.6-slim
ARG user
ARG password
ADD requirements.lock /
RUN pip install --upgrade --extra-index-url https://$user:$password@distribution.livetech.site -r /requirements.lock
ADD . /loko-gateway
ENV PYTHONPATH=$PYTHONPATH:/loko-gateway
WORKDIR /loko-gateway/loko_gateway/services
CMD python services.py
