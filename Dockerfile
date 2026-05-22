FROM quay.io/jupyter/base-notebook:python-3.13

COPY --chown=${NB_USER}:users . /home/${NB_USER}/src
COPY --chown=${NB_USER}:users examples /home/${NB_USER}/examples

RUN cd /home/${NB_USER}/src && \
    python -m pip install --upgrade pip && \
    python -m pip install . --group docker && \
    python -m pip check

RUN cd /home/${NB_USER}/examples && \
    jupytext --to ipynb *.md && \
    rm *.md && \
    rm -rf /home/${NB_USER}/.cache && \
    rm -rf /home/${NB_USER}/src
