"""PreM3 application package.

Do not import the ADK agent at package import time. The isolated Meridian EDA
worker loads ``app.tools`` without google-adk installed.
"""
