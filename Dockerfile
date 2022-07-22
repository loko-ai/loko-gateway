FROM python:3.7.12-slim-bullseye
ARG user
ARG password
ADD requirements.lock /
RUN pip install --user --upgrade --extra-index-url https://$user:$password@distribution.livetech.site -r /requirements.lock

# FROM python:3.7-slim
# COPY --from=builder /root/.local /root/.local
ADD . /ds4biz-agateway
ENV PYTHONPATH=$PYTHONPATH:/ds4biz-agateway
WORKDIR /ds4biz-agateway/ds4biz_agateway/services
CMD python services.py