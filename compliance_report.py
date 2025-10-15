#!/usr/bin/env python3
"""
Cloud202 Compliance & Security Report Generator
Generates specialized compliance assessment reports for regulated industries
Companion tool to the Executive Report Generator
"""

import json
import os
import logging
import boto3
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import re
import sys

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas

# Import shared styling components
from report_styles import NumberedCanvas, create_enhanced_styles

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ComplianceReportGenerator:
    """Generate compliance-focused assessment reports"""

    def __init__(self, aws_region: str = "us-east-1"):
        self.aws_region = aws_region
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            self.bedrock_runtime = boto3.client(
                service_name='bedrock-runtime',
                region_name=aws_region
            )
            # Use inference profile ARN
            self.model_id = 'arn:aws:bedrock:us-east-1:781364298443:inference-profile/us.anthropic.claude-sonnet-4-5-20250929-v1:0'
            logger.info("✅ AWS Bedrock client initialized")
            logger.info(f"🤖 Using model: {self.model_id}")
        except Exception as e:
            logger.warning(f"⚠️ Bedrock not available: {e}")
            self.bedrock_runtime = None

        self.output_dir = Path("reports")
        self.output_dir.mkdir(exist_ok=True)

    def load_assessment_data(self, json_file_path: str) -> Dict[str, Any]:
        """Load assessment data from JSON"""
        with open(json_file_path, 'r', encoding='utf-8') as file:
            return json.load(file)

    def process_assessment_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process assessment data"""
        responses = raw_data.get('responses', {})
        
        business_owner = responses.get('business-owner', '')
        if ',' in business_owner:
            company_name = business_owner.split(',')[0].strip()
        else:
            company_name = responses.get('company-name', 'Valued Customer')
        
        industry = self._infer_industry(responses)
        
        return {
            'company_name': company_name,
            'industry': industry,
            'responses': responses,
            'assessment_date': raw_data.get('exportDate', datetime.now().isoformat())[:10]
        }

    def _infer_industry(self, responses: Dict) -> str:
        """Infer industry from responses"""
        problem = responses.get('business-problems', '').lower()
        
        if any(word in problem for word in ['clinical', 'physician', 'patient', 'healthcare', 'medical']):
            return 'Healthcare Technology'
        elif any(word in problem for word in ['financial', 'banking', 'fintech', 'payment', 'trading', 'market', 'advisory']):
            return 'Financial Technology'
        else:
            return 'Technology'

    def should_generate_compliance_report(self, industry: str) -> bool:
        """Check if compliance report is needed"""
        regulated_industries = ['healthcare', 'financial', 'finance', 'banking']
        return any(ind in industry.lower() for ind in regulated_industries)

    def create_compliance_prompt(self, processed_data: Dict[str, Any]) -> str:
        """Create compliance report prompt"""
        
        company_name = processed_data.get('company_name', 'Customer')
        industry = processed_data.get('industry', 'Technology')
        
        prompt = f"""ROLE: You are a senior compliance and security consultant creating a specialized assessment report for regulated industries.

COMPANY: {company_name}
INDUSTRY: {industry}
ASSESSMENT DATA: {json.dumps(processed_data, indent=2)}

Generate a comprehensive compliance and security report with 4 sections for 10-15 page PDF.

Return ONLY valid JSON:
{{
  "compliance_gap_analysis": "...",
  "data_governance_framework": "...",
  "security_architecture": "...",
  "regulatory_roadmap": "..."
}}

REQUIREMENTS:

1. COMPLIANCE GAP ANALYSIS (3-4 pages / 1000-1200 words):
- Identify applicable regulations for {industry} (HIPAA/HITECH for healthcare, SOX/PCI-DSS/GLBA for financial, GDPR for all)
- Map each regulation to specific AWS compliance services (Artifact, Config, Security Hub, CloudTrail, KMS, Macie)
- Assess current compliance posture with gap identification
- Prioritize gaps by risk level (Critical/High/Medium/Low)
- Provide detailed remediation roadmap with specific AWS services
- Address data residency, sovereignty, cross-border transfers
- Include 5-6 detailed paragraphs with subheadings

2. DATA GOVERNANCE FRAMEWORK (3-4 pages / 1000-1200 words):
- Define 4-tier data classification (Public, Internal, Confidential, Restricted)
- Specify access control models (RBAC with IAM roles, ABAC with tags)
- Detail audit trail requirements (CloudTrail, CloudWatch, S3 access logs, VPC Flow Logs)
- Privacy protection measures (encryption with KMS, anonymization, tokenization, DLP with Macie)
- Data lifecycle management (S3 lifecycle, retention policies, secure deletion)
- AWS services mapping for each requirement
- 5-6 detailed paragraphs with technical specifications

3. SECURITY ARCHITECTURE (2-3 pages / 800-1000 words):
- Security controls framework (NIST CSF, CIS Controls, ISO 27001 alignment)
- Threat modeling for {industry} AI workloads (data breaches, model attacks, prompt injection)
- Network security (VPC design, security groups, NACLs, WAF, Shield)
- Incident response procedures with runbooks
- Security monitoring (Security Hub, GuardDuty, CloudWatch, EventBridge)
- Encryption specifications (at rest with KMS, in transit with TLS 1.3)
- 4-5 detailed paragraphs with architecture details

4. REGULATORY ROADMAP (2-3 pages / 800-1000 words):
- 12-month compliance timeline with monthly milestones
- Phase 1 (Months 1-3): Foundation controls
- Phase 2 (Months 4-6): Enhanced security and monitoring
- Phase 3 (Months 7-9): Certification preparation
- Phase 4 (Months 10-12): Audits and continuous monitoring
- Required certifications (SOC 2, ISO 27001, industry-specific)
- Documentation requirements and evidence collection
- Compliance cost estimates ($250K-500K initial, $150K-300K annual)
- 4-5 detailed paragraphs with timeline details

FORMATTING:
- Professional compliance tone suitable for legal/compliance officers
- Specific regulatory citations
- Detailed AWS service configurations
- Risk-based prioritization
- Audit-ready documentation style
- Include specific implementation guidance

Return ONLY JSON with 4 sections. No markdown."""

        return prompt

    def generate_compliance_content(self, processed_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate compliance content using Bedrock"""
        
        if self.bedrock_runtime:
            try:
                logger.info("🤖 Generating compliance report content...")
                
                prompt = self.create_compliance_prompt(processed_data)
                
                body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 12000,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3
                }
                
                response = self.bedrock_runtime.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps(body)
                )
                
                response_body = json.loads(response.get('body').read())
                content_text = response_body.get('content')[0].get('text')
                
                content_text = re.sub(r'```json\n?', '', content_text)
                content_text = re.sub(r'```\n?', '', content_text)
                content_text = content_text.strip()
                
                content = json.loads(content_text)
                logger.info("✅ Compliance content generated")
                return content
                
            except Exception as e:
                logger.error(f"❌ Bedrock generation failed: {e}")
                return self._generate_fallback_compliance_content(processed_data)
        else:
            return self._generate_fallback_compliance_content(processed_data)

    def _generate_fallback_compliance_content(self, processed_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate fallback compliance content"""
        
        company_name = processed_data.get('company_name', 'Customer')
        industry = processed_data.get('industry', 'Technology')
        
        # Determine regulations
        if 'financial' in industry.lower() or 'fintech' in industry.lower():
            regulations = ['SOX (Sarbanes-Oxley)', 'PCI-DSS (Payment Card Industry)', 'GLBA (Gramm-Leach-Bliley)', 'GDPR']
            primary_regs = "SOX, PCI-DSS, GLBA, and GDPR"
        elif 'healthcare' in industry.lower():
            regulations = ['HIPAA (Health Insurance Portability)', 'HITECH Act', 'GDPR']
            primary_regs = "HIPAA, HITECH, and GDPR"
        else:
            regulations = ['GDPR', 'ISO 27001']
            primary_regs = "GDPR and ISO 27001"
        
        return {
            'compliance_gap_analysis': f"""COMPLIANCE GAP ANALYSIS

Regulatory Requirements Mapping

{company_name}, operating in the {industry} sector, must comply with multiple regulatory frameworks including {primary_regs}. This comprehensive gap analysis evaluates the organization's current compliance posture, identifies critical deficiencies, and provides a prioritized remediation roadmap aligned with regulatory timelines and business objectives.

The regulatory landscape for {industry} organizations implementing Generative AI solutions encompasses stringent requirements for data protection, privacy safeguards, security controls, comprehensive audit trails, and industry-specific mandates. Non-compliance can result in substantial financial penalties ranging from millions of dollars, significant reputational damage, operational restrictions, and potential criminal liability for executives.

Applicable Regulatory Frameworks and Requirements

{company_name} must adhere to the following primary regulatory frameworks, each imposing specific technical and procedural requirements:

For organizations in the {industry} sector, {primary_regs} establish comprehensive requirements covering multiple dimensions of data protection and operational security. Each framework specifies particular technical controls, extensive documentation standards, regular audit requirements, and ongoing compliance validation procedures that must be maintained continuously.

Data protection requirements mandate encryption of sensitive data at rest and in transit, strict access controls based on least privilege principles, comprehensive audit logging of all data access and modifications, and data breach notification procedures with specific timelines. Privacy requirements include obtaining valid consent for data processing, providing data subject rights (access, rectification, erasure, portability), implementing privacy by design principles, and conducting data protection impact assessments for high-risk processing activities.

Security requirements encompass multi-layered security controls including network segmentation, intrusion detection and prevention systems, vulnerability management programs, security incident response procedures, and regular security testing including penetration testing and vulnerability assessments. Audit and documentation requirements mandate maintaining detailed records of all data processing activities, security controls implementation, access logs, incident response actions, and compliance validation activities.

Data residency requirements mandate that certain categories of data must remain within specific geographic boundaries to comply with local data protection laws. Cross-border data transfer mechanisms require appropriate safeguards including Standard Contractual Clauses (SCCs), Binding Corporate Rules (BCRs), or adequacy determinations from regulatory authorities. Organizations must document legal bases for international transfers and conduct transfer impact assessments.

AWS Compliance Services Mapping

Amazon Web Services provides extensive compliance capabilities and certifications supporting regulatory requirements, significantly reducing the compliance burden compared to on-premises infrastructure through the shared responsibility model.

AWS Artifact provides on-demand access to AWS compliance reports and certifications including SOC 1/2/3 reports, ISO 27001 certification, PCI-DSS Attestation of Compliance, HIPAA Business Associate Agreement, FedRAMP authorization packages, and numerous country-specific certifications. This service enables organizations to obtain necessary compliance documentation for their own audit and certification processes.

AWS Config enables continuous compliance monitoring and assessment through configurable rules that automatically evaluate AWS resource configurations against organizational policies and regulatory requirements. Pre-built managed rules map directly to common compliance frameworks including CIS AWS Foundations Benchmark, PCI-DSS, HIPAA, and NIST frameworks. Custom rules can be developed for organization-specific compliance requirements.

AWS Security Hub provides centralized security and compliance posture management across multiple AWS accounts and regions. It aggregates security findings from AWS services including GuardDuty, Inspector, Macie, and IAM Access Analyzer, as well as third-party security tools. Security Hub includes automated compliance checks against standards including CIS AWS Foundations Benchmark, PCI-DSS, and AWS Foundational Security Best Practices.

AWS CloudTrail provides comprehensive audit logging of all API calls and user activities across AWS infrastructure, creating an immutable audit trail supporting forensic investigations and compliance audits. CloudTrail logs capture the identity of the API caller, time of the API call, source IP address, request parameters, and response elements. Log file integrity validation ensures audit log authenticity.

AWS Key Management Service (KMS) provides centralized cryptographic key management with hardware security module (HSM) protection meeting FIPS 140-2 requirements. KMS enables encryption at rest for virtually all AWS services and supports automatic key rotation, detailed access logging, and fine-grained access controls through IAM policies and key policies.

Amazon Macie uses machine learning to automatically discover, classify, and protect sensitive data including personally identifiable information (PII), financial data, and healthcare information stored in Amazon S3. Macie provides continuous monitoring, data access pattern analysis, and automated alerting for anomalous data access or potential data leaks.

Current Compliance Posture Assessment

Comprehensive assessment of {company_name}'s current compliance capabilities reveals several areas requiring immediate attention and enhancement to meet regulatory standards. While existing security controls provide foundational protection, significant gaps exist in audit trail coverage, automated compliance monitoring, real-time security alerting, and formal documentation of security procedures and data handling practices.

Infrastructure security controls currently lack comprehensive configuration management, automated compliance validation, and centralized security monitoring across all systems and applications. Existing access controls do not fully implement least privilege principles, and privileged access lacks sufficient monitoring and approval workflows. Multi-factor authentication is not consistently enforced across all access paths, creating authentication vulnerabilities.

Data protection measures require enhancement including comprehensive encryption implementation for all data at rest using industry-standard encryption algorithms, mandatory encryption for all data in transit using TLS 1.3 or higher, and proper encryption key management with separation of duties. Current data classification procedures are informal and inconsistent, resulting in insufficient protection for sensitive data categories.

Audit and logging capabilities have significant gaps including incomplete logging coverage across all systems and applications, insufficient log retention periods not meeting regulatory requirements, lack of centralized log aggregation and analysis, and absence of real-time monitoring and alerting for security and compliance events. Existing logs lack tamper-evident storage protections required for compliance audits.

Documentation of security procedures, data handling practices, incident response capabilities, and compliance validation activities needs formalization and regular updating. Data protection impact assessments have not been conducted for high-risk AI processing activities. Privacy notices and consent mechanisms require development to support data subject rights.

Critical Compliance Gaps and Prioritization

High-priority gaps (must address within 3 months) requiring immediate remediation include:

Insufficient data classification and handling procedures: Implement formal data classification scheme with automated classification using Amazon Macie, define handling requirements for each classification level, apply classification labels to all data assets, and establish data lifecycle management procedures. This gap poses high risk for regulatory violations and data breaches.

Incomplete audit trail coverage: Deploy AWS CloudTrail across all AWS accounts and regions with log file validation enabled, implement centralized log storage in dedicated security account with encryption and access controls, configure CloudWatch Logs for application and system logging, enable S3 access logging and VPC Flow Logs, and establish log retention periods meeting regulatory requirements (minimum 7 years for regulated industries). Inadequate audit trails prevent effective incident investigation and fail compliance audit requirements.

Limited encryption implementation: Enable encryption for all data at rest using AWS KMS with automatic key rotation, implement mandatory TLS 1.3 for all data in transit, deploy encryption for all database systems including RDS and DynamoDB, enable S3 bucket encryption with KMS keys, and implement envelope encryption for application-level data protection. Unencrypted data violates regulatory requirements and exposes sensitive information to unauthorized access.

Gaps in access control enforcement: Implement role-based access control (RBAC) using AWS IAM with least privilege principle, deploy attribute-based access control (ABAC) using resource tags for fine-grained permissions, enforce multi-factor authentication (MFA) for all users especially privileged accounts, implement privileged access management with approval workflows and session recording, and establish regular access reviews with automated remediation of excessive permissions. Inadequate access controls represent primary risk factor for data breaches and insider threats.

Documentation and privacy compliance gaps: Develop comprehensive documentation of data processing activities including legal bases and retention periods, create data protection impact assessments for AI processing activities, implement privacy notices and consent management mechanisms, establish data subject rights request procedures with 30-day response timeframes, and document security controls implementation and validation activities. Missing documentation fails compliance audits and exposes organization to regulatory enforcement actions.

Medium-priority gaps (address within 6 months) requiring near-term attention include:

Incomplete security monitoring coverage: Deploy AWS Security Hub for centralized security posture management, implement Amazon GuardDuty for intelligent threat detection using machine learning, configure AWS Config rules for automated compliance checking, establish security alerting and incident response procedures, and integrate with Security Information and Event Management (SIEM) system for advanced analytics. Limited security monitoring delays threat detection and incident response.

Limited incident response procedures: Develop formal incident response plan with defined roles and responsibilities, establish incident classification criteria and escalation procedures, create incident response runbooks for common scenarios, implement automated incident response capabilities using AWS Systems Manager and Lambda, conduct regular incident response tabletop exercises, and establish forensic investigation procedures using AWS CloudTrail and CloudWatch Logs Insights. Inadequate incident response capabilities increase breach impact and regulatory penalties.

Insufficient vendor management controls: Implement vendor risk assessment procedures for all third-party service providers processing sensitive data, require vendor security certifications and audit reports, establish vendor contract requirements for security controls and data protection, conduct regular vendor security reviews, and maintain vendor inventory with risk classifications. Vendor risks represent significant compliance exposure through supply chain vulnerabilities.

Gaps in compliance training programs: Develop role-based compliance training covering regulatory requirements and organizational policies, implement annual training requirements with completion tracking, create specialized training for developers on secure coding and data protection, establish privacy training for personnel handling personal information, and conduct regular security awareness campaigns. Insufficient training leads to human errors causing compliance violations and security incidents.""",

            'data_governance_framework': f"""DATA GOVERNANCE FRAMEWORK

Introduction to Data Governance

Comprehensive data governance framework establishes clear policies, standardized procedures, and technical controls for data management throughout its complete lifecycle from creation through secure destruction. This framework provides the foundation for regulatory compliance, risk management, and business value realization from data assets while ensuring data quality, security, and privacy protection.

Effective data governance for {company_name}'s GenAI implementation requires integration across multiple dimensions including data classification and protection, access controls and permissions management, comprehensive audit trails and documentation, privacy protection measures, data lifecycle management, and data quality assurance. Each component must align with regulatory requirements while supporting business objectives and operational efficiency.

Data Classification Scheme and Handling Standards

Four-tier data classification system addresses varying sensitivity levels with appropriate protection measures:

Public data includes information specifically approved for public disclosure requiring no confidentiality controls but maintaining integrity and availability protections. Examples include marketing materials, press releases, and published financial reports. Public data may be stored on public-facing systems, transmitted without encryption if integrity is protected, and accessed without authentication controls. However, integrity controls prevent unauthorized modification.

Internal data encompasses general business information intended for internal use only requiring basic access controls and protection measures. Examples include internal communications, operational procedures, and non-sensitive business analytics. Internal data requires authentication for access, encryption for transmission outside secure internal networks, access logging, and backup protection. Inappropriate disclosure poses limited business risk but should be prevented.

Confidential data includes sensitive business information, customer data, personal information, and intellectual property requiring strict access controls, encryption, and comprehensive audit trails. Examples include customer account information, employee records, business strategies, source code, and AI model training data. Confidential data requires role-based access controls with least privilege, encryption at rest and in transit, comprehensive access logging, regular access reviews, data loss prevention controls, and secure disposal procedures. Unauthorized disclosure poses significant business and regulatory risk.

Restricted data encompasses highly sensitive information such as payment card data, protected health information, social security numbers, authentication credentials, and encryption keys requiring maximum protection controls. Restricted data requires explicit authorization for access, multi-factor authentication, encryption with HSM-backed keys, real-time access monitoring and alerting, field-level encryption or tokenization, minimal data retention, and certified secure disposal procedures. Unauthorized access or disclosure poses severe business, legal, and regulatory consequences.

Each classification level specifies detailed handling requirements including authorized storage locations (on-premises secure data centers, AWS regions with specific data residency requirements), mandatory encryption requirements (algorithm specifications, key management procedures), access control models (authentication requirements, authorization criteria), retention periods aligned with business needs and regulatory mandates, secure disposal procedures (secure deletion methods, certificate of destruction), and transmission requirements (encryption protocols, approved transmission channels).

Data classification labels must be applied to all data assets at creation time with automated classification for unstructured data using Amazon Macie's machine learning capabilities. Macie automatically discovers and classifies sensitive data including personally identifiable information (PII), financial information, and credentials, and continuously monitors data access patterns to detect anomalies indicating potential data leaks or policy violations.

Access Control and Permission Models

Role-Based Access Control (RBAC) provides the primary access control mechanism for {company_name} using AWS Identity and Access Management (IAM) roles mapped to specific job functions and data classification access requirements. Each role receives the minimum permissions necessary to perform assigned duties, implementing the principle of least privilege.

Standard user roles include: Data Scientists with access to anonymized training data and development environments; Application Developers with access to non-production environments and appropriate code repositories; Business Analysts with read-only access to aggregate analytics and reporting systems; System Administrators with infrastructure management permissions but no direct access to sensitive business data; Security Administrators with monitoring and audit access across all systems; and Compliance Officers with read-only access to all systems for compliance validation purposes.

Privileged roles requiring enhanced controls include: Database Administrators with access to production databases subject to break-glass procedures and session recording; Security Engineers with permissions to modify security controls requiring approval workflows; Cloud Infrastructure Administrators with broad AWS permissions subject to MFA and session time limits; and Audit Administrators with ability to access all audit logs but no capability to modify business data or systems.

Attribute-Based Access Control (ABAC) enables fine-grained access decisions based on user attributes, resource attributes (tags), and environmental context. ABAC policies evaluate multiple factors including user department and job title, resource classification level and project assignment, time of day and geographic location, and device security posture and network origin. This approach provides dynamic access control adapting to changing contexts while maintaining security.

AWS IAM policies implement access controls using JSON policy documents with explicit allow and deny statements. Policies follow security best practices including explicit deny rules for high-risk actions, conditions restricting access based on source IP, MFA requirements, and time constraints, and regular policy reviews to remove unused permissions. Service Control Policies (SCPs) enforce organizational security boundaries across all AWS accounts preventing even account administrators from violating security policies.

Least privilege principle requires that users and services receive only the specific permissions required for their functions, with permissions grants being time-limited where possible. Regular access reviews (quarterly for privileged access, annually for standard access) ensure permissions remain appropriate as roles and responsibilities change. Automated access recertification workflows prompt managers to review and approve continued access, with automatic revocation of access not explicitly recertified.

Privileged access management provides enhanced controls for administrative functions including mandatory multi-factor authentication using hardware tokens or biometric authentication, session recording capturing all privileged activities for audit and investigation purposes, approval workflows requiring managerial authorization for sensitive privileged actions, just-in-time access provisioning granting temporary elevated permissions only when needed, and privileged session monitoring with real-time alerting for suspicious activities.

AWS IAM Access Analyzer continuously analyzes resource policies to identify resources shared with external entities, helping prevent unintended access. GuardDuty monitors for compromised credentials and anomalous access patterns indicating potential account compromise. CloudWatch anomaly detection identifies unusual access patterns requiring investigation.

Audit Trails and Documentation Requirements

Comprehensive audit trail coverage captures all data access, modifications, and administrative actions supporting regulatory compliance requirements, forensic investigations, and security monitoring. Audit logs must be tamper-evident, retained for appropriate periods, and readily searchable for investigations and compliance audits.

AWS CloudTrail logs all API calls across AWS infrastructure including the identity of API caller (IAM user, role, or AWS service), timestamp of API call, source IP address of caller, request parameters submitted, and response elements returned. CloudTrail provides event history for 90 days by default with optional extended retention in S3 buckets with encryption and access controls. Log file integrity validation using digital signatures ensures audit log authenticity and detects tampering attempts.

Multi-region CloudTrail trails ensure complete audit coverage across all AWS regions including capturing management events (control plane operations like creating instances), data events (data plane operations like S3 object access), and insights events (unusual API call patterns). Organization trails automatically enable logging for all accounts in AWS Organizations providing centralized audit visibility.

Amazon CloudWatch Logs centralizes application and system logs with real-time monitoring, automated alerting, and long-term retention. Log groups organize logs by application or system with configurable retention periods meeting regulatory requirements (7 years minimum for financial services, 6 years for healthcare). CloudWatch Logs Insights provides SQL-like query language for log analysis and investigation. Subscription filters stream logs to other services for additional processing or archival.

S3 access logging tracks all requests to S3 buckets including requester identity, bucket name, request time, request action, response status, and error codes. Access logs enable detection of unauthorized access attempts, unusual access patterns, and compliance validation. VPC Flow Logs capture network traffic metadata including source and destination IP addresses, ports, protocol, packet and byte counts, and action taken (accept or reject). Flow logs support network security analysis, compliance auditing, and troubleshooting.

Database audit logging tracks query execution and data modifications across relational and NoSQL databases. Amazon RDS audit logging captures database connections, queries executed, database objects accessed, and privilege changes. DynamoDB streams provide time-ordered sequence of item-level modifications enabling audit trails for NoSQL data. Aurora provides advanced auditing capabilities with granular control over logged events and minimal performance impact.

Application logging captures business logic execution, user activities within applications, transaction processing steps, error conditions and exceptions, and security-relevant events like authentication attempts and authorization decisions. Structured logging using JSON format enables efficient parsing and analysis. Centralized logging infrastructure aggregates logs from distributed applications and microservices.

Log retention periods align with regulatory requirements varying by industry and data type. Financial services regulations typically require 7-year retention for transaction-related logs. Healthcare regulations require 6-year minimum retention for health information access logs. Privacy regulations require retention periods matching data processing retention. Legal hold requirements may mandate extended retention for specific log categories.

Log analysis and monitoring detect anomalous access patterns, potential security incidents, and compliance violations in real-time. Security Information and Event Management (SIEM) integration enables advanced threat detection through correlation analysis across multiple log sources. Machine learning models identify unusual patterns indicating compromised accounts, data exfiltration attempts, or insider threats. Automated alerting notifies security teams of high-priority events requiring immediate investigation.

Log protection measures prevent unauthorized access and tampering. CloudTrail log files stored in dedicated S3 buckets with encryption using AWS KMS keys and restrictive bucket policies preventing deletion or modification. S3 Object Lock provides write-once-read-many (WORM) protection for compliance requirements. Logs transmitted to SIEM systems using encrypted channels with authentication. Log access requires privileged permissions with comprehensive audit trails of log access themselves.""",

            'security_architecture': f"""SECURITY ARCHITECTURE

Security Controls Framework and Standards Alignment

Comprehensive security architecture implements defense-in-depth strategy with multiple layers of preventive, detective, and responsive security controls addressing the full spectrum of cybersecurity risks. The security framework aligns with industry-standard frameworks including NIST Cybersecurity Framework (CSF), CIS Controls, and ISO 27001 standards providing structured approach to security program development and maturity assessment.

NIST Cybersecurity Framework provides organizing structure across five core functions: Identify (asset management, business environment, governance, risk assessment), Protect (access control, data security, protective technology), Detect (anomalies and events, security monitoring, detection processes), Respond (response planning, communications, analysis, mitigation, improvements), and Recover (recovery planning, improvements, communications). Each function includes specific categories and subcategories mapping to technical controls and operational procedures.

CIS Controls provide prioritized set of cybersecurity best practices proven to defend against common attack patterns. Priority controls include inventory and control of hardware and software assets, continuous vulnerability management, controlled use of administrative privileges, secure configuration for hardware and software, controlled access based on need to know, malware defenses, audit log management, email and web browser protections, and penetration testing and red team exercises. Implementation of CIS Controls significantly reduces cybersecurity risk.

ISO 27001 information security management system (ISMS) provides internationally recognized framework for managing information security through systematic approach to risk management. ISO 27001 requires establishing security policy, conducting risk assessments, implementing security controls from ISO 27002, conducting internal audits, and continuous improvement through management review. ISO 27001 certification demonstrates commitment to information security and provides competitive advantage.

Network Security Architecture and Controls

Multi-layer network security architecture implements isolation, segmentation, and monitoring controls protecting against external attacks, lateral movement, and data exfiltration. Amazon Virtual Private Cloud (VPC) provides isolated network environment with complete control over virtual networking including IP address ranges, subnets, route tables, and network gateways.

Network segmentation strategy creates multiple security zones with different trust levels. Public subnets host internet-facing components like load balancers and web servers with strict inbound security controls. Private subnets host application servers and business logic with no direct internet access. Isolated subnets host database servers and sensitive data stores with highly restricted access controls. Each security zone implements defense-in-depth with multiple security control layers.

Security groups implement stateful firewall rules at instance and elastic network interface level controlling inbound and outbound traffic based on protocol, port, and source/destination. Security group rules follow least privilege principle allowing only specifically required traffic. Network Access Control Lists (NACLs) provide stateless subnet-level traffic filtering as additional defense layer. NACLs enable explicit deny rules for known malicious IP addresses or traffic patterns.

AWS Web Application Firewall (WAF) protects web applications against common exploits and vulnerabilities including SQL injection attacks, cross-site scripting (XSS), and command injection. WAF provides managed rule groups addressing OWASP Top 10 vulnerabilities, rate-based rules preventing abuse and DDoS attacks, geographic restrictions blocking traffic from specific countries, IP reputation lists blocking known malicious sources, and custom rules for application-specific protection requirements. WAF integrates with CloudFront CDN and Application Load Balancer for comprehensive protection.

AWS Shield provides managed DDoS protection defending against volumetric attacks, state exhaustion attacks, and application layer attacks. Shield Standard provides automatic protection against common DDoS attacks at no additional cost. Shield Advanced provides enhanced DDoS protection, 24/7 DDoS Response Team (DRT) support, cost protection against scaling costs during attacks, and real-time attack visibility and reporting.

VPC endpoints enable private connectivity to AWS services without internet exposure reducing attack surface. Interface endpoints powered by AWS PrivateLink provide private IP addresses for AWS services. Gateway endpoints provide private connections to S3 and DynamoDB through route table entries. Private connectivity eliminates data exfiltration risks through public internet.

AWS Network Firewall provides advanced network protection with stateful inspection, intrusion prevention capabilities, protocol detection and filtering, domain name filtering, and custom rule support. Network Firewall deployed at VPC perimeter inspects all traffic entering or leaving VPC. Managed rule groups from AWS partners provide threat intelligence-based protections.

Identity and Access Management Controls

Zero trust security model assumes no implicit trust based on network location requiring authentication and authorization for every access request. Multi-factor authentication (MFA) mandatory for all privileged access and strongly recommended for all users. MFA adds security layer beyond passwords requiring physical token, mobile device authentication, or biometric verification.

AWS Identity and Access Management (IAM) implements fine-grained access controls through policies defining permissions. IAM policies specify allowed or denied actions on specific resources with optional conditions. Policy conditions restrict access based on source IP address, MFA authentication status, time of day, requested region, resource tags, and encryption requirements. IAM roles enable secure service-to-service authentication without embedded credentials in code.

AWS IAM Identity Center (formerly AWS SSO) provides centralized identity management with integration to corporate identity providers including Active Directory, Okta, Azure AD, and other SAML 2.0 providers. Identity Center enables single sign-on across multiple AWS accounts and business applications with consistent access policies and centralized user management. Automatic provisioning and deprovisioning synchronizes user accounts with corporate identity source.

Privileged Access Management (PAM) controls administrative access through enhanced security measures. AWS Systems Manager Session Manager provides secure shell access to EC2 instances without opening inbound ports, maintaining bastion hosts, or managing SSH keys. Session Manager integrates with IAM for authentication, logs all session activity to CloudTrail and CloudWatch, supports session recording for audit purposes, and enables temporary elevated access with automatic session termination.

Encryption and Data Protection

Encryption protects data confidentiality throughout the data lifecycle. AWS Key Management Service (KMS) provides centralized cryptographic key management with hardware security module (HSM) protection meeting FIPS 140-2 Level 2 requirements (Level 3 for CloudHSM). KMS manages encryption keys with automatic rotation, usage auditing through CloudTrail, and fine-grained access controls through key policies and IAM policies.

Data at rest encryption protects stored data using AES-256 encryption algorithm. Amazon S3 encrypts objects using server-side encryption with KMS keys, S3 managed keys, or customer-provided keys. Amazon EBS encrypts volumes with transparent encryption requiring no application changes. Amazon RDS encrypts databases including automated backups and read replicas. Amazon Redshift encrypts data warehouse with cluster encryption. DynamoDB encrypts tables with encryption at rest enabled by default for new tables.

Data in transit encryption protects data during transmission using Transport Layer Security (TLS) 1.3 protocol. All AWS API calls use HTTPS with TLS encryption. VPC traffic can be encrypted using IPsec VPN or AWS PrivateLink. Application-level encryption using TLS 1.3 protects data transmitted between application components. Certificate management through AWS Certificate Manager automates certificate provisioning, renewal, and deployment.

Threat Modeling for GenAI Workloads

Threat modeling identifies potential security threats specific to GenAI workloads in {industry} sector enabling proactive security controls. Primary threat categories include data breaches compromising training data or inference inputs/outputs, model theft extracting proprietary AI models through API abuse, adversarial attacks manipulating model outputs through crafted inputs, prompt injection attacks bypassing security controls through malicious prompts, training data poisoning corrupting model behavior through manipulated training data, and model inversion attacks extracting sensitive training data from model outputs.

Data breach threats addressed through encryption at rest and in transit, strict access controls with least privilege, comprehensive audit logging, data loss prevention using Amazon Macie, network segmentation isolating sensitive data, and exfiltration detection monitoring data transfers. Model theft prevention includes API rate limiting preventing model extraction through excessive queries, authentication and authorization for model access, model output monitoring detecting extraction patterns, intellectual property protection through model obfuscation, and usage tracking identifying suspicious access patterns.

Adversarial attack mitigations include input validation sanitizing inference inputs, output filtering detecting and blocking malicious outputs, anomaly detection identifying unusual input patterns, model robustness testing with adversarial examples, and ensemble models reducing attack effectiveness. Prompt injection protections encompass input sanitization removing malicious commands, prompt templates constraining input formats, output validation ensuring responses match expected patterns, semantic analysis detecting injection attempts, and user education on prompt safety.

Security Monitoring and Threat Detection

Continuous security monitoring detects threats, compliance violations, and anomalous behavior enabling rapid response. AWS Security Hub provides centralized security and compliance posture management across multiple AWS accounts and regions. Security Hub aggregates findings from AWS native security services and third-party tools, performs automated compliance checks against security standards, prioritizes findings based on severity and context, and triggers automated remediation workflows.

Amazon GuardDuty provides intelligent threat detection using machine learning and threat intelligence. GuardDuty analyzes CloudTrail logs detecting compromised credentials, unusual API calls, and privilege escalation. VPC Flow Logs analysis identifies reconnaissance activity, backdoor communications, data exfiltration, and cryptocurrency mining. DNS logs analysis detects domain generation algorithms and communication with command and control servers. GuardDuty provides actionable findings with severity ratings and remediation guidance.

AWS Config monitors resource configurations against security baselines and compliance rules. Config provides configuration history tracking changes over time, compliance dashboards showing overall posture, automated remediation fixing non-compliant resources, and conformance packs implementing compliance as code. Pre-built conformance packs available for PCI-DSS, HIPAA, NIST frameworks, and CIS benchmarks.

CloudWatch provides real-time monitoring with custom metrics, dashboards, and alarms. CloudWatch anomaly detection uses machine learning to identify unusual patterns in metrics without manual threshold configuration. EventBridge enables event-driven security automation triggering Lambda functions or Systems Manager automation for automated incident response.

Incident Response Procedures

Structured incident response procedures enable rapid detection, containment, eradication, and recovery from security incidents minimizing impact. Incident response team includes security operations center personnel, incident response manager, forensic analysts, legal counsel, compliance officers, communications team, and executive leadership. 24/7 security operations center monitors security alerts and initiates response procedures.

Incident detection through automated monitoring generates alerts for potential security events. Security Hub and GuardDuty findings trigger automated workflows classifying incidents based on severity, impact, and confidence. Incident classification determines appropriate response procedures and escalation requirements. Critical incidents (confirmed data breach, ransomware, critical system compromise) trigger immediate escalation to executive leadership and initiate crisis management procedures.

Containment procedures isolate affected systems preventing threat spread. Automated containment revokes compromised credentials, applies restrictive security group rules, isolates compromised instances, and blocks malicious IP addresses. Manual containment includes network segmentation, system shutdown if necessary, and evidence preservation for forensic investigation. Containment balances security needs with business continuity requirements.

Forensic investigation uses CloudTrail logs providing complete audit trail of actions, CloudWatch logs containing application activity, VPC Flow Logs showing network communications, and system snapshots preserving evidence. Forensic analysis determines incident scope, attack vectors, compromised systems and data, persistence mechanisms, and attribution indicators. Investigation findings inform eradication and recovery procedures.

Eradication removes threats and vulnerabilities enabling safe system recovery. Activities include removing malware and backdoors, patching exploited vulnerabilities, resetting compromised credentials, rebuilding compromised systems from clean backups or images, and implementing additional security controls preventing recurrence. Validation ensures complete threat removal before returning systems to production.

Recovery validates system integrity and returns to normal operations. Recovery procedures include restoring data from backups, validating system configurations, conducting security testing, monitoring for indicators of persistence, and gradually returning services to production. Enhanced monitoring during recovery period detects any remaining threats.

Post-incident review conducted within one week of incident resolution documents timeline of events, effectiveness of response procedures, lessons learned, and recommendations for improvement. Action items implemented to strengthen security controls and response capabilities. Incident metrics tracked including mean time to detect, mean time to contain, and mean time to recover enabling continuous improvement.""",

            'regulatory_roadmap': f"""REGULATORY ROADMAP

Compliance Implementation Timeline Overview

Structured 12-month roadmap establishes clear milestones, deliverables, and accountability for achieving and maintaining regulatory compliance. Phased approach balances urgency of compliance requirements with practical implementation constraints, available resources, and business continuity needs. Each phase includes specific objectives, key activities, deliverables, resource requirements, and success criteria enabling progress tracking and stakeholder communication.

Compliance program implementation requires sustained executive commitment, dedicated resources, and organizational change management. Timeline assumes typical enterprise implementation with moderate complexity. Actual timelines may vary based on organization size, regulatory scope, existing control maturity, resource availability, and appetite for parallel workstreams versus sequential implementation.

Phase 1: Foundation and Assessment (Months 1-3)

Foundation phase establishes compliance program structure, conducts comprehensive gap assessment, and implements critical baseline controls addressing highest-risk areas. This phase focuses on "quick wins" demonstrating progress while building foundation for sustained compliance.

Month 1 activities include compliance program establishment with executive sponsorship, dedicated compliance team formation, compliance management framework definition, stakeholder identification and engagement, regulatory requirements inventory specific to {industry} sector, and compliance technology platform selection for GRC (governance, risk, compliance) management.

Critical immediate actions include enabling AWS CloudTrail across all AWS accounts with log file validation, implementing S3 bucket encryption for all existing buckets, configuring basic security monitoring with AWS Security Hub, conducting initial security assessment identifying critical vulnerabilities, and establishing incident response notification procedures.

Month 2 focuses on comprehensive gap assessment including detailed evaluation of current controls against regulatory requirements, risk assessment prioritizing gaps by likelihood and impact, compliance roadmap refinement based on findings, resource planning and budget allocation, and vendor assessment for third-party compliance dependencies.

Data inventory and classification activities begin with comprehensive data discovery across all systems, preliminary data classification based on sensitivity, data flow mapping showing data movement and processing, data retention analysis identifying regulatory requirements, and documentation of data processing activities required by privacy regulations.

Month 3 delivers foundational security controls including implementation of data classification scheme with initial tagging, deployment of encryption at rest for all sensitive data using KMS, establishment of privileged access management with MFA enforcement, configuration of comprehensive audit logging across all systems, and development of initial compliance documentation including policies and procedures.

Phase 1 deliverables include compliance program charter with executive approval, comprehensive gap assessment report with prioritized remediation roadmap, complete data inventory with preliminary classifications, foundational security controls operational including encryption and logging, initial compliance documentation package, and Phase 2 detailed implementation plan with resource allocations.

Success criteria for Phase 1 include executive sponsorship secured with budget approved, CloudTrail enabled across 100% of accounts, encryption enabled for 90%+ of sensitive data stores, data inventory completed covering 80%+ of known data stores, and compliance team fully staffed and trained.

Phase 2: Control Implementation and Enhancement (Months 4-6)

Enhancement phase implements comprehensive security controls, establishes automated compliance monitoring, and addresses medium-priority gaps identified in assessment. Focus shifts from basic controls to advanced security capabilities and compliance automation.

Month 4 activities include AWS Security Hub full deployment with automated compliance checks against PCI-DSS, HIPAA, or relevant standards, Amazon GuardDuty threat detection enablement across all accounts, AWS Config rules deployment for automated compliance monitoring, centralized security monitoring dashboard creation, and security incident response playbook development for common scenarios.

Data governance enhancement includes finalization of data classification with automated classification using Amazon Macie, implementation of role-based access control with comprehensive IAM policies, deployment of data loss prevention monitoring, establishment of data lifecycle policies with automated enforcement, and privacy program development including consent management and data subject rights procedures.

Month 5 focuses on network security architecture enhancements including VPC security hardening with security groups and NACLs review, AWS WAF deployment for web application protection, Network Firewall implementation for advanced protection, private connectivity establishment using VPC endpoints and PrivateLink, and network segmentation enforcement separating environments by sensitivity.

Vendor risk management program implementation includes vendor inventory development with risk classifications, vendor security assessment procedures, vendor contract review for security and compliance requirements, ongoing vendor monitoring processes, and vendor incident response coordination procedures.

Month 6 delivers advanced security capabilities including encryption key management optimization with automated rotation, security monitoring enhancement with custom detection rules, incident response automation using Lambda and Systems Manager, vulnerability management program with continuous scanning, and penetration testing planning and scoping.

Phase 2 deliverables include Security Hub operational with compliance dashboards, GuardDuty threat detection fully configured, AWS Config rules deployed covering all critical resources, complete data classification with labels applied, enhanced IAM policies implementing least privilege, vendor risk management program operational, and advanced security monitoring with automated alerting.

Success criteria include automated compliance monitoring covering 90%+ of resources, data classification applied to 95%+ of data assets, security monitoring detecting threats within 15 minutes, access control violations reduced by 80%, and vendor assessments completed for all critical vendors.

Phase 3: Certification Preparation and Testing (Months 7-9)

Certification preparation phase focuses on evidence collection, control testing, gap remediation, and audit readiness activities preparing for formal compliance certifications and external audits.

Month 7 activities include external audit firm selection and engagement, audit scope definition and planning, compliance evidence collection for all implemented controls, internal control testing validating effectiveness, and gap remediation for any remaining findings from internal assessments.

Evidence management includes systematic collection of control evidence including policy documents, configuration screenshots, audit logs demonstrating control operation, test results validating control effectiveness, training records proving personnel competency, and incident response documentation showing capability maturity. Evidence organized in GRC platform or evidence management system for efficient audit support.

Month 8 focuses on pre-audit preparation including mock audit or readiness assessment by external consultant, findings remediation addressing any gaps identified, process improvement based on mock audit feedback, audit artifact preparation organizing evidence packages, and stakeholder preparation briefing personnel on audit processes and expectations.

Compliance training program rollout includes role-based training covering regulatory requirements, security awareness training for all personnel, specialized training for developers on secure coding practices, privacy training for personnel handling personal data, incident response training with tabletop exercises, and training effectiveness measurement with knowledge assessments.

Month 9 delivers audit readiness validation including final internal control testing, evidence package completion, corrective action plan development for any remaining gaps, management representation letter preparation, and audit logistics coordination including audit schedule, workspace, and access.

Phase 3 deliverables include complete evidence package for all controls, internal control testing results documenting effectiveness, corrective action plans for any gaps, compliance training completed by 100% of personnel, mock audit completed with findings remediated, and audit readiness confirmed by internal compliance team.

Success criteria include all critical and high-priority controls tested and passing, evidence complete for 100% of audit scope, corrective actions completed for 95%+ of findings, compliance training completion rate >95%, and mock audit result indicating high likelihood of certification success.

Phase 4: Audit Execution and Continuous Monitoring (Months 10-12)

Final phase executes formal compliance audits, obtains certifications, and establishes continuous compliance monitoring ensuring sustained adherence between audit cycles.

Month 10 activities include formal compliance audit execution with external auditors, audit evidence provision and auditor support, audit finding response addressing any observations, supplemental evidence collection if required, and preliminary audit results review with management.

Applicable certifications for {company_name} may include SOC 2 Type II demonstrating security, availability, processing integrity, confidentiality, and privacy controls over minimum 6-month period (typically 9-12 months for initial audit). SOC 2 audit includes testing of control design and operating effectiveness with detailed testing of each control objective. Cost estimate: $50,000-$150,000 for initial certification depending on scope and complexity. Annual recertification required.

ISO 27001 certification demonstrates information security management system meeting international standard. ISO 27001 requires comprehensive ISMS documentation, risk assessment and treatment, control implementation from ISO 27002, internal audit program, and management review. Three-year certification cycle with annual surveillance audits. Cost estimate: $75,000-$200,000 for initial certification. Surveillance audits $25,000-$50,000 annually.

Industry-specific certifications include HITRUST CSF for healthcare combining HIPAA requirements with other security frameworks, PCI-DSS for payment card processing requiring quarterly vulnerability scans and annual audits, FedRAMP for government cloud services with rigorous authorization process, and other regional or sector-specific certifications as applicable.

Month 11 focuses on audit completion and remediation including management response to audit findings, remediation plan development and execution, final audit report receipt, certification report issuance, and certification announcement and market communication if appropriate.

Continuous compliance monitoring establishment includes automated compliance checking with AWS Config and Security Hub, compliance dashboard creation for executive visibility, monthly compliance reporting to management and board, quarterly compliance program reviews, and annual compliance program maturity assessment.

Month 12 delivers ongoing compliance operations including compliance monitoring and reporting processes, audit maintenance procedures, regulatory change monitoring, compliance calendar with key dates and deadlines, next audit cycle planning, and compliance program continuous improvement.

Phase 4 deliverables include completed compliance audit with certification obtained, audit findings remediated with documented evidence, continuous compliance monitoring operational, compliance reporting and governance established, and audit maintenance program operational.

Required Documentation and Evidence Collection

Comprehensive documentation supports compliance audits and provides evidence of control implementation and effectiveness. Documentation categories include policies and procedures defining security and compliance requirements, system documentation describing architecture and configurations, risk assessments identifying and evaluating threats, audit logs demonstrating control operation, test results validating control effectiveness, training records proving competency, incident response documentation showing capability and maturity, vendor assessments evaluating third-party risks, compliance certifications from AWS and other vendors, and management reviews demonstrating governance oversight.

Evidence management system organizes and indexes evidence for efficient audit support. Annual evidence refresh ensures documentation currency and accuracy. Many organizations leverage GRC platforms automating evidence collection, management, and audit workflow including ServiceNow GRC, Archer, OneTrust, or purpose-built compliance management tools.

Ongoing Compliance Monitoring and Maintenance

Continuous compliance program maintains regulatory adherence between formal certification audits. Automated compliance monitoring through AWS Config rules provides real-time compliance status with automatic detection of non-compliant resources. Security Hub compliance standards provide continuous assessment against frameworks including CIS AWS Foundations Benchmark, PCI-DSS, and NIST frameworks.

Monthly compliance dashboards report key metrics to management including compliance posture percentage, number of compliance violations by severity, mean time to remediate violations, control testing results, security incident summary, and audit readiness status. Quarterly compliance reviews assess control effectiveness, review compliance metrics trends, evaluate emerging risks, update compliance documentation, and identify improvement opportunities.

Annual compliance program assessment evaluates program maturity using frameworks like CMMI (Capability Maturity Model Integration) or custom maturity models. Assessment identifies advancement opportunities including process optimization, automation enhancement, tool consolidation, and capability expansion. Board reporting provides executive and board visibility into compliance posture, key risks, program investments, and strategic direction.

Regulatory change monitoring tracks new regulations and regulatory guidance requiring program updates. Monitoring sources include regulatory agency websites and publications, industry association compliance alerts, legal counsel guidance, compliance management service subscriptions, and participation in industry working groups. Change impact assessments evaluate new requirements and determine necessary program modifications.

Compliance Cost Estimates and Resource Planning

Initial compliance program establishment costs $250,000-$500,000 including external consultant fees for gap assessment and remediation guidance ($75,000-$150,000), audit and certification fees for SOC 2 and/or ISO 27001 ($75,000-$200,000), compliance management tool licensing ($25,000-$50,000 annually), staff training and certifications ($25,000-$50,000), and internal resource allocation for dedicated compliance team (2-4 FTE).

Annual ongoing compliance costs $150,000-$300,000 including annual audit and recertification fees ($50,000-$100,000), compliance monitoring and management tool fees ($25,000-$50,000), continuous training programs ($15,000-$30,000), external consultant support for specialized needs ($25,000-$50,000), regulatory monitoring services ($10,000-$20,000), and internal resource allocation for compliance team (2-3 FTE).

Cost optimization strategies include leveraging AWS native compliance capabilities reducing need for third-party tools, automating evidence collection reducing manual effort, establishing efficient repeatable processes, training internal team reducing dependence on external consultants, and coordinating multiple certifications reducing redundant effort. Shared responsibility model with AWS reduces compliance scope and costs compared to on-premises infrastructure through AWS inherited controls.

Third-Party Audit Coordination and Management

Effective audit coordination ensures smooth efficient audit process minimizing business disruption while demonstrating compliance. Pre-audit preparation conducted 1-2 months before audit includes evidence package assembly organizing all control documentation, internal control testing validating effectiveness before external testing, gap remediation addressing any control weaknesses, audit logistics planning including scheduling and access provisioning, and stakeholder briefing preparing personnel for audit interviews.

Audit fieldwork support during audit execution includes providing timely evidence to auditors, coordinating personnel interviews, explaining control designs and implementations, providing system access for testing, responding to auditor questions and information requests, and maintaining positive auditor relationship. Dedicated audit liaison coordinates all audit activities reducing business disruption.

Finding remediation after audit fieldwork addresses audit observations and recommendations. Findings classified by severity including material weaknesses requiring immediate remediation, significant deficiencies requiring near-term attention, and observations providing improvement opportunities. Management response letters document remediation plans, responsible parties, target completion dates, and implementation status. Timely remediation critical for certification issuance and demonstrates commitment to compliance.

Post-audit activities include implementing process improvements based on audit recommendations, updating documentation reflecting lessons learned, planning next audit cycle, communicating results to stakeholders, and celebrating team success. Continuous improvement mindset uses audit feedback to strengthen compliance program maturity and effectiveness over time.

This comprehensive regulatory roadmap provides {company_name} with clear path to compliance achievement and sustained adherence supporting business objectives while meeting regulatory obligations and managing compliance risks effectively."""
        }


    def create_title_page(self, styles, customer_data):
        """Create compliance report title page"""
        elements = []
        
        # Add space at top
        elements.append(Spacer(1, 1.5 * inch))
        
        # Main title
        title = Paragraph("Cloud202", styles['TitlePage'])
        elements.append(title)
        elements.append(Spacer(1, 0.2 * inch))
        
        # Subtitle
        subtitle = Paragraph("Compliance & Security Solutions", styles['Subtitle'])
        elements.append(subtitle)
        elements.append(Spacer(1, 0.5 * inch))
        
        # Report type
        report_type = Paragraph("Compliance & Security<br/>Assessment Report", styles['TitlePage'])
        elements.append(report_type)
        elements.append(Spacer(1, 1 * inch))
        
        # Customer name
        company_name = customer_data.get("company_name", "")
        if company_name:
            customer_title = Paragraph(f"<b>Prepared for:</b><br/>{company_name}", styles['Subtitle'])
            elements.append(customer_title)
        
        elements.append(Spacer(1, 0.5 * inch))
        
        # Details table
        details_data = [
            ['Industry:', customer_data.get('industry', 'Technology')],
            ['Assessment Type:', 'Compliance & Security'],
            ['Assessment Date:', customer_data.get('assessment_date', datetime.now().strftime('%Y-%m-%d'))]
        ]
        
        details_table = Table(details_data, colWidths=[2*inch, 3*inch])
        details_table.setStyle(TableStyle([
            ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 11),
            ('FONT', (1, 0), (1, -1), 'Helvetica', 11),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2d3748')),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(details_table)
        
        elements.append(Spacer(1, 1 * inch))
        
        # Report date
        date_text = f"<b>Report Date:</b> {datetime.now().strftime('%B %d, %Y')}"
        date_para = Paragraph(date_text, styles['Subtitle'])
        elements.append(date_para)
        
        elements.append(Spacer(1, 0.3 * inch))
        
        # Confidentiality notice
        conf_text = "<b>CONFIDENTIAL - Cloud202 Compliance & Security Assessment</b>"
        conf_para = Paragraph(conf_text, styles['Subtitle'])
        elements.append(conf_para)
        
        elements.append(PageBreak())
        
        return elements

    def create_content_section(self, title: str, content: str, styles):
        """Create content section"""
        elements = []
        
        # Section title
        section_title = Paragraph(title, styles['MainHeading'])
        elements.append(section_title)
        elements.append(Spacer(1, 0.2 * inch))
        
        # Process content
        if content.strip():
            # Split into paragraphs
            paragraphs = content.split('\n\n')
            
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                
                # Check if it's a subsection header (starts with capital letter and ends with colon or is short)
                if (para.endswith(':') or (len(para.split()) <= 8 and para[0].isupper())) and len(para) < 100:
                    # Subsection heading
                    subsection = Paragraph(para, styles['SubsectionHeading'])
                    elements.append(subsection)
                    elements.append(Spacer(1, 0.1 * inch))
                else:
                    # Regular paragraph
                    paragraph = Paragraph(para, styles['BodyText'])
                    elements.append(paragraph)
                    elements.append(Spacer(1, 0.08 * inch))
        
        elements.append(PageBreak())
        
        return elements
        
    def create_pdf(self, content: Dict[str, str], customer_info: Dict[str, Any], output_path: str):
        """Create compliance PDF"""
        logger.info(f"📄 Creating compliance PDF: {output_path}")
        
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=1 * inch,
            title=f"Compliance Assessment - {customer_info.get('company_name')}",
            author="Cloud202 Compliance Team"
        )
        
        styles = create_enhanced_styles()
        elements = []
        
        # Title page
        elements.extend(self.create_title_page(styles, customer_info))
        
        # Content sections
        sections = [
            ("Compliance Gap Analysis", content.get('compliance_gap_analysis', '')),
            ("Data Governance Framework", content.get('data_governance_framework', '')),
            ("Security Architecture", content.get('security_architecture', '')),
            ("Regulatory Roadmap", content.get('regulatory_roadmap', ''))
        ]
        
        for title, text in sections:
            elements.extend(self.create_content_section(title, text, styles))
        
        # Build PDF with custom canvas for page numbers
        def make_canvas(*args, **kwargs):
            kwargs['report_type'] = 'Compliance & Security Assessment'
            return NumberedCanvas(*args, **kwargs)
        doc.build(elements, canvasmaker=make_canvas)
        logger.info(f"✅ Compliance PDF created: {output_path}")

    def generate_report(self, json_file_path: str = None, force: bool = False):
        """Generate compliance report"""
        try:
            logger.info("🚀 Starting compliance report generation...")
            
            if not json_file_path:
                json_file_path = input("\n📄 Enter JSON assessment file path: ").strip().strip("\"'")
            
            raw_data = self.load_assessment_data(json_file_path)
            processed_data = self.process_assessment_data(raw_data)
            
            # Check if compliance report is needed (allow override via force)
            if (not force) and (not self.should_generate_compliance_report(processed_data['industry'])):
                logger.info(f"⚠️  Compliance report not applicable for {processed_data['industry']}")
                print(f"\n⚠️  Compliance report is designed for regulated industries")
                print("   (Healthcare, Financial Services, Government)")
                print(f"   Current industry: {processed_data['industry']}")
                return None
            
            logger.info(f"✅ Compliance report applicable for {processed_data['industry']}")
            
            company_name = re.sub(r'[^\w\-_]', '_', processed_data['company_name'].lower())
            output_filename = f"Compliance_Security_Report_{company_name}_{self.timestamp}"
            pdf_file = self.output_dir / f"{output_filename}.pdf"
            
            # Generate content
            content = self.generate_compliance_content(processed_data)
            
            # Create PDF
            self.create_pdf(content, processed_data, str(pdf_file))
            
            results = {
                'pdf_path': str(pdf_file),
                'company_name': processed_data['company_name'],
                'industry': processed_data['industry'],
                'timestamp': self.timestamp
            }
            
            logger.info("✅ Compliance report generation completed!")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            raise


def main():
    """Main function"""
    print("\n" + "="*70)
    print("🔒 Cloud202 Compliance & Security Report Generator")
    print("="*70)
    print("📋 Specialized compliance assessment for regulated industries")
    print("="*70)
    
    try:
        generator = ComplianceReportGenerator(aws_region="us-east-1")
        results = generator.generate_report()
        
        if results:
            print("\n" + "="*70)
            print("✅ COMPLIANCE & SECURITY REPORT GENERATED SUCCESSFULLY!")
            print("="*70)
            print(f"📁 Output: {results['pdf_path']}")
            print(f"🏢 Company: {results['company_name']}")
            print(f"🏭 Industry: {results['industry']}")
            print(f"⏰ Generated: {results['timestamp']}")
            print("="*70)
            print("\n🎉 Your compliance report is ready!")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted. Goodbye!")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())