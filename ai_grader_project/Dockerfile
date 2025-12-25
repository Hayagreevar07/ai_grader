FROM python:3.9

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

# Install dependencies
# We use the CPU version of torch to keep the image size smaller if possible, 
# but for simplicity and compatibility we stick to the requirements file.
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy the application code
COPY . /code

# Create directories for uploads and set permissions
RUN mkdir -p /code/uploads && chmod 777 /code/uploads

# Set the default port for HG Spaces
ENV PORT=7860

# Command to run the application
CMD ["gunicorn", "-b", "0.0.0.0:7860", "app:app"]
