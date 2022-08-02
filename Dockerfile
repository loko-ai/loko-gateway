FROM python:3.10-slim
ARG user
ARG password
ADD requirements.lock /
RUN pip install --user --upgrade --extra-index-url https://$user:$password@distribution.livetech.site -r /requirements.lock

# FROM python:3.7-slim
# COPY --from=builder /root/.local /root/.local
ADD . /loko-gateway
ENV PYTHONPATH=$PYTHONPATH:/loko-gateway
WORKDIR /loko-gateway/loko_gateway/services
CMD python services.py