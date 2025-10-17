"""
Centralized Bedrock Configuration for All Report Generators
Provides standardized settings for AWS Bedrock model access
"""

import os
import boto3
import botocore.config
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class BedrockConfig:
    """Centralized Bedrock configuration for all report types"""
    
    # Model Configuration
    # Strands BedrockModel expects a Bedrock model ID, not an inference profile ARN
    # Use Claude 3.7 Sonnet per project guidelines for Strands integrations
    DEFAULT_MODEL_ID = "anthropic.claude-3-7-sonnet-20250219-v1:0"
    
    # Regional inference profile ARNs
    INFERENCE_PROFILES = {
        "us-east-1": "arn:aws:bedrock:us-east-1:781364298443:inference-profile/us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "eu-west-1": "arn:aws:bedrock:eu-west-1:781364298443:inference-profile/eu.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "eu-west-2": "arn:aws:bedrock:eu-west-2:781364298443:inference-profile/eu.anthropic.claude-sonnet-4-5-20250929-v1:0",
    }
    
    # Default regions by report type
    DEFAULT_REGIONS = {
        "executive": "eu-west-2",
        "technical": "eu-west-2",
        "compliance": "eu-west-2",
    }
    
    # Token limits by report type
    TOKEN_LIMITS = {
        "executive": 16000,  # 12-15 pages
        "technical": 25000,  # 30-40 pages
        "compliance": 20000,  # 15-20 pages
    }
    
    # Timeouts removed by request — operations will not use read/connect timeouts
    
    # Branding configuration
    BRANDING = {
        "company_name": "Cloud202",
        "tool_name": "Qubitz",
        "contact_email": "hello@cloud202.com",
        "contact_phone": "+44 7792 565738",
    }
    
    @staticmethod
    def get_model_id(region: str = None) -> str:
        """
        Return the Bedrock model ID for use with SDK wrappers like Strands.
        """
        return BedrockConfig.DEFAULT_MODEL_ID

    @staticmethod
    def get_inference_profile_arn(region: str = None) -> str:
        """
        Return the regional inference profile ARN for direct Bedrock client calls.
        Defaults to us-east-1 if region not provided/known.
        """
        region = region or "us-east-1"
        return BedrockConfig.INFERENCE_PROFILES.get(region, BedrockConfig.INFERENCE_PROFILES["us-east-1"])
    
    @staticmethod
    def get_boto_config(report_type: str = "executive") -> botocore.config.Config:
        """
        Get boto3 configuration without timeouts
        
        Args:
            report_type: Type of report (executive, technical, compliance)
            
        Returns:
            Configured botocore.config.Config object
        """
        # Explicitly configure no read/connect timeouts
        return botocore.config.Config(
            read_timeout=None,
            connect_timeout=None,
            retries={'max_attempts': 2, 'mode': 'adaptive'}
        )
    
    @staticmethod
    def create_bedrock_client(region: str = None, report_type: str = "executive") -> boto3.client:
        """
        Create a configured Bedrock runtime client
        
        Args:
            region: AWS region (defaults to us-east-1)
            report_type: Type of report for appropriate timeout configuration
            
        Returns:
            Configured boto3 bedrock-runtime client
        """
        region = region or BedrockConfig.DEFAULT_REGIONS.get(report_type, "us-east-1")
        boto_config = BedrockConfig.get_boto_config(report_type)
        
        client = boto3.client(
            'bedrock-runtime',
            region_name=region,
            config=boto_config
        )
        
        logger.info(f"✅ Created Bedrock client for {report_type} in {region}")
        # No timeout configured
        
        return client
    
    @staticmethod
    def get_token_limit(report_type: str = "executive") -> int:
        """
        Get the appropriate token limit for a report type
        
        Args:
            report_type: Type of report (executive, technical, compliance)
            
        Returns:
            Maximum token limit for the report type
        """
        return BedrockConfig.TOKEN_LIMITS.get(report_type, 16000)
    
    @staticmethod
    def get_region(report_type: str = "executive") -> str:
        """
        Get the default region for a report type
        
        Args:
            report_type: Type of report (executive, technical, compliance)
            
        Returns:
            Default AWS region for the report type
        """
        # Check environment variable first
        env_region = os.getenv("AWS_REGION") or os.getenv("BEDROCK_REGION")
        if env_region:
            return env_region
            
        return BedrockConfig.DEFAULT_REGIONS.get(report_type, "us-east-1")
    
    @staticmethod
    def get_branding() -> Dict[str, str]:
        """
        Get branding configuration (can be overridden by environment variables)
        
        Returns:
            Dictionary with branding information
        """
        return {
            "company_name": os.getenv("COMPANY_NAME", BedrockConfig.BRANDING["company_name"]),
            "tool_name": os.getenv("TOOL_NAME", BedrockConfig.BRANDING["tool_name"]),
            "contact_email": os.getenv("CONTACT_EMAIL", BedrockConfig.BRANDING["contact_email"]),
            "contact_phone": os.getenv("CONTACT_PHONE", BedrockConfig.BRANDING["contact_phone"]),
        }
    
    @staticmethod
    def log_configuration(report_type: str = "executive", region: str = None):
        """
        Log the current Bedrock configuration
        
        Args:
            report_type: Type of report being generated
            region: AWS region being used
        """
        region = region or BedrockConfig.get_region(report_type)
        model_id = BedrockConfig.get_model_id(region)
        token_limit = BedrockConfig.get_token_limit(report_type)
        
        logger.info("=" * 60)
        logger.info(f"🔧 Bedrock Configuration for {report_type.upper()} Report")
        logger.info("=" * 60)
        logger.info(f"🌍 Region: {region}")
        logger.info(f"🤖 Model: {model_id}")
        logger.info(f"🎯 Max Tokens: {token_limit}")
        logger.info("=" * 60)

