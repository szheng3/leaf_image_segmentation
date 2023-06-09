import cv2
import numpy as np
import requests
import segmentation_models_pytorch as smp
import streamlit as st
import torch
import torchvision.transforms as transforms
from PIL import Image
from camera_input_live import camera_input_live


# Function to send email using API
def send_email_api(name, to_email, subject, body):
    url = "https://apiv1.sszzz.me/api/email/send"
    payload = {
        "name": name,
        "email": to_email,
        "subject": subject,
        "body": body
    }
    response = requests.post(url, json=payload)
    return response.status_code


device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# Load the pre-trained models
def load_trained_models(model_name):
    # Set the device (either CPU or GPU) for training
    print(device)
    model_architecture, encoder_name = model_name.split('_')

    # Choose the appropriate model architecture based on the input
    if model_architecture == "UNET":
        model = smp.Unet(encoder_name=encoder_name, encoder_weights=None, in_channels=3, classes=1)
    elif model_architecture == "DeepLabV3":
        model = smp.DeepLabV3(encoder_name=encoder_name, encoder_weights=None, in_channels=3, classes=1)
    elif model_architecture == "UNETplus":
        model = smp.UnetPlusPlus(encoder_name=encoder_name, encoder_weights=None, in_channels=3, classes=1)
    else:
        raise ValueError("Invalid model architecture")

    # Load the pre-trained model weights
    model.load_state_dict(torch.load(f"./trained_models/{model_name}.pth", map_location=device))
    model = model.to(device)
    return model


def display_sent_email(uploaded_file):
    if uploaded_file is not None:
        # Open the uploaded image and convert it to RGB format
        image = Image.open(uploaded_file).convert("RGB")
        # Display the uploaded image and segmented image side by side
        cols = st.columns(2)
        resized_image = image.resize((256, 256))
        cols[0].image(resized_image, caption="Uploaded Image", use_column_width=True)
        video_transformer = VideoTransformer(model)
        output_image = video_transformer.transform(image)
        cols[1].image(output_image, caption="Segmented Image", use_column_width=True)
        # Check if the segmented area is greater than the threshold percentage
        area_percentage = (np.count_nonzero(output_image) / (
                output_image.shape[0] * output_image.shape[1] * output_image.shape[2])) * 100
        # If the area percentage is greater than the threshold, send an email alert
        if area_percentage > threshold_percentage:
            st.write(f"The predicted area percentage is {area_percentage:.2f}% which is greater than the threshold.")
            print(email)
            if email:
                # Send an email alert
                print("Sending email...")
                subject = "Image Segmentation Alert"
                body = f"The predicted area percentage is {area_percentage:.2f}% which is greater than the threshold of {threshold_percentage}%."
                try:
                    send_email_api("Leaf Image Segmentation", subject, body, email)
                    st.success("Alert email sent successfully.")
                except Exception as e:
                    st.error(f"Error sending email: {e}")
        else:
            st.write(f"The predicted area percentage is {area_percentage:.2f}% which is below the threshold.")


class VideoTransformer:
    def __init__(self, model):
        self.model = model
        self.data_transform = transforms.Compose([
            transforms.Resize((256, 256)),
            transforms.ToTensor(),
        ])

    def transform(self, image):
        # Transform the input image and send it to the device
        input_image = self.data_transform(image).unsqueeze(0).to(device)

        # Perform segmentation
        with torch.no_grad():
            self.model.eval()
            preds = torch.sigmoid(self.model(input_image))
            threshold = 0.1
            preds = (preds > threshold).float()

        # Display the output image
        output_image = preds.squeeze().cpu().numpy() * 255
        segmented_frame = cv2.cvtColor(np.uint8(output_image), cv2.COLOR_GRAY2BGR)
        return segmented_frame


# App
st.set_page_config(page_title="Leaf Image Segmentation", layout="wide")
st.title("Leaf Image Segmentation")
st.write("Upload an image or use the camera to capture a photo and select a pre-trained model for segmentation.")

# Sidebar for settings and configurations
sidebar = st.sidebar
sidebar.title("Settings")
sidebar.write("Select a pre-trained model:")
model_names = ["efficientnet-b7", "efficientnet-b0", "resnet34", "resnet101", "vgg16", "vgg19"]
model_nets = ["UNETplus", "DeepLabV3", "UNET"]
# Remove DeepLabV3_vgg16 and DeepLabV3_vgg19 from the available options
allowed_combinations = [f"{net}_{encoder}" for net in model_nets for encoder in model_names
                        if not (net == "DeepLabV3" and encoder in ["vgg16", "vgg19"])]
# Select the pre-trained model
model_name = sidebar.selectbox("", allowed_combinations)
model = load_trained_models(model_name)
# Set the threshold percentage for email alerts
threshold_percentage = sidebar.slider("Alert Threshold Percentage", min_value=0, max_value=100, value=50, step=1)
sidebar.write("Email Subscription:")
# Email subscription input
email = sidebar.text_input("Enter your email", "")
# Navigation between Upload Image and Use Camera options
nav = sidebar.radio("Navigation", ["Upload Image", "Use Camera"])

if nav == "Upload Image":
    # Upload image file
    uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        display_sent_email(uploaded_file)
else:
    # Use the camera to capture a photo
    st.write("Use the camera:")
    image = camera_input_live()
    display_sent_email(image)
