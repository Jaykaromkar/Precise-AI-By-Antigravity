import aiosmtplib
import logging
from typing import Optional
from email.message import EmailMessage
from datetime import datetime
from core.config import settings

async def send_html_email(to_email: str, subject: str, html_content: str, attachment_data: Optional[bytes] = None, attachment_name: Optional[str] = None):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = settings.SMTP_USERNAME
    msg['To'] = to_email
    
    msg.add_alternative(html_content, subtype='html')
    
    if attachment_data and attachment_name:
        msg.add_attachment(attachment_data, maintype='application', subtype='pdf', filename=attachment_name)
        
    try:
        is_ssl = (settings.SMTP_PORT == 465)
        is_tls = getattr(settings, "SMTP_PORT", 587) == 587

        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USERNAME,
            password=settings.SMTP_PASSWORD,
            use_tls=is_ssl,
            start_tls=is_tls
        )
        logging.info(f"Email sent successfully to {to_email}")
    except Exception as e:
        logging.error(f"Failed to send email to {to_email}: {str(e)}")

def get_base_html(title: str, content: str, header_gradient: str = "linear-gradient(135deg, #3b82f6, #10b981)") -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; background-color: #0f172a; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
        <div style="background-color: #0f172a; padding: 40px 20px; min-height: 100vh;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #1e293b; border-radius: 16px; overflow: hidden; box-shadow: 0 20px 40px rgba(0,0,0,0.4); border: 1px solid #334155;">
                
                <!-- Header -->
                <div style="background: {header_gradient}; padding: 35px 20px; text-align: center;">
                    <h1 style="color: #ffffff; font-size: 26px; font-weight: 700; margin: 0; letter-spacing: 1px; text-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                        {title}
                    </h1>
                </div>

                <!-- Body -->
                <div style="padding: 40px 35px; color: #cbd5e1; line-height: 1.7; font-size: 16px;">
                    {content}
                </div>

                <!-- Footer -->
                <div style="background-color: #0f172a; padding: 24px; text-align: center; border-top: 1px solid #334155;">
                    <p style="color: #64748b; font-size: 13px; margin: 0;">&copy; 2026 Precise AI Financial Operations. All rights reserved.</p>
                    <p style="color: #475569; font-size: 12px; margin: 8px 0 0 0;">This is an automated security message.</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

async def send_welcome_email(to_email: str, username: str, password: str):
    content = f"""
        <p style="margin-top: 0; font-size: 18px; color: #f8fafc;">Hello <strong>{username}</strong>,</p>
        <p>Your premium Financial Analysis dashboard is now fully provisioned and ready for use. Below are your secure credentials for the platform:</p>
        
        <div style="background: rgba(15, 23, 42, 0.6); padding: 25px; border-left: 4px solid #3b82f6; border-radius: 8px; margin: 30px 0; border-top: 1px solid #334155; border-right: 1px solid #334155; border-bottom: 1px solid #334155;">
            <p style="margin: 0; color: #94a3b8; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px;">Username</p>
            <p style="margin: 4px 0 20px 0; color: #f8fafc; font-size: 18px; font-weight: 500;">{username}</p>
            
            <p style="margin: 0; color: #94a3b8; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px;">Temporary Password</p>
            <p style="margin: 4px 0 0 0; color: #f8fafc; font-size: 18px; font-weight: 500; font-family: monospace; background: #0f172a; padding: 6px 12px; border-radius: 4px; display: inline-block;">{password}</p>
        </div>
        
        <p>For your security, please do not share this email. You may log in directly using the link below.</p>
        
        <div style="text-align: center; margin: 40px 0 10px 0;">
            <a href="http://localhost:8000/" style="display: inline-block; background: linear-gradient(to right, #2563eb, #3b82f6); color: #ffffff; padding: 16px 36px; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px; letter-spacing: 0.5px; box-shadow: 0 4px 14px rgba(37, 99, 235, 0.4); text-transform: uppercase;">Access Dashboard</a>
        </div>
    """
    html = get_base_html("Welcome to Precise AI", content, "linear-gradient(135deg, #2563eb, #10b981)")
    await send_html_email(to_email, "Welcome to Precise AI - Your Credentials", html)

async def send_login_alert(to_email: str, username: str):
    content = f"""
        <p style="margin-top: 0; font-size: 18px; color: #f8fafc;">Hello <strong>{username}</strong>,</p>
        <p>This is a security notification. A new secure login was just successfully authenticated on your Precise AI workspace.</p>
        
        <div style="background: rgba(15, 23, 42, 0.6); padding: 25px; border-left: 4px solid #8b5cf6; border-radius: 8px; margin: 30px 0; border: 1px solid #334155;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <div style="width: 12px; height: 12px; border-radius: 50%; background-color: #10b981; box-shadow: 0 0 10px #10b981;"></div>
                <p style="margin: 0; color: #f8fafc; font-size: 16px; font-weight: 500;">Authentication Successful</p>
            </div>
            <p style="margin: 15px 0 0 0; color: #94a3b8; font-size: 14px;">The connection was established over a secure encrypted channel.</p>
        </div>
        
        <p style="color: #94a3b8; font-size: 14px;">If this was you, no further action is needed. If you did not authorize this login, please contact systems administration immediately.</p>
        
        <div style="text-align: center; margin: 40px 0 10px 0;">
            <a href="http://localhost:8000/" style="display: inline-block; background: #334155; color: #f8fafc; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 500; font-size: 15px; border: 1px solid #475569;">Review Account Activity</a>
        </div>
    """
    html = get_base_html("Security Alert: Login Detected", content, "linear-gradient(135deg, #6366f1, #a855f7)")
    await send_html_email(to_email, "Precise AI - Security Alert", html)

async def send_password_recovery(to_email: str, username: str, password: str):
    content = f"""
        <p style="margin-top: 0; font-size: 18px; color: #f8fafc;">Hello <strong>{username}</strong>,</p>
        <p>A request was made to recover the credentials for your Precise AI account. As requested, your secure access details are below:</p>
        
        <div style="background: rgba(15, 23, 42, 0.6); padding: 25px; border-left: 4px solid #f59e0b; border-radius: 8px; margin: 30px 0; border-top: 1px solid #334155; border-right: 1px solid #334155; border-bottom: 1px solid #334155;">
            <p style="margin: 0; color: #94a3b8; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px;">Username</p>
            <p style="margin: 4px 0 20px 0; color: #f8fafc; font-size: 18px; font-weight: 500;">{username}</p>
            
            <p style="margin: 0; color: #94a3b8; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px;">Recovered Password</p>
            <p style="margin: 4px 0 0 0; color: #f8fafc; font-size: 18px; font-weight: 500; font-family: monospace; background: #0f172a; padding: 6px 12px; border-radius: 4px; display: inline-block;">{password}</p>
        </div>
        
        <p style="color: #94a3b8; font-size: 14px;">If you did not make this request, please completely ignore this email.</p>
        
        <div style="text-align: center; margin: 40px 0 10px 0;">
            <a href="http://localhost:8000/" style="display: inline-block; background: linear-gradient(to right, #f59e0b, #d97706); color: #ffffff; padding: 16px 36px; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px; letter-spacing: 0.5px; box-shadow: 0 4px 14px rgba(245, 158, 11, 0.3); text-transform: uppercase;">Log In Now</a>
        </div>
    """
    html = get_base_html("Password Recovery Request", content, "linear-gradient(135deg, #f59e0b, #ea580c)")
    await send_html_email(to_email, "Precise AI - Password Recovery", html)

async def send_report_ready_email(to_email: str, username: str, filename: str, document_id: int, pdf_buffer: Optional[bytes] = None):
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ margin: 0; padding: 0; background-color: #0f172a; font-family: 'Segoe UI', system-ui, sans-serif; -webkit-font-smoothing: antialiased; color: #cbd5e1; }}
            .container {{ max-width: 600px; margin: 40px auto; background: #1e293b; border-radius: 16px; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5); border: 1px solid #334155; }}
            .header {{ background: linear-gradient(135deg, #10b981, #0ea5e9); padding: 50px 30px; text-align: center; }}
            .header h1 {{ color: #ffffff; font-size: 28px; font-weight: 800; margin: 0; letter-spacing: -0.5px; text-shadow: 0 2px 4px rgba(0,0,0,0.2); }}
            .header p {{ color: #f0fdfa; font-size: 16px; margin: 10px 0 0 0; opacity: 0.9; }}
            
            .content {{ padding: 40px; }}
            .greeting {{ font-size: 20px; color: #f8fafc; margin-top: 0; margin-bottom: 20px; }}
            
            .meta-box {{ background: rgba(15, 23, 42, 0.4); border-left: 4px solid #3b82f6; padding: 20px; border-radius: 8px; margin: 30px 0; border: 1px solid #334155; }}
            .meta-label {{ color: #94a3b8; font-size: 12px; text-transform: uppercase; font-weight: 700; letter-spacing: 1px; margin: 0 0 4px 0; }}
            .meta-value {{ color: #f8fafc; font-size: 18px; font-weight: 600; margin: 0; }}
            
            .grid {{ display: table; width: 100%; margin: 30px 0; border-spacing: 15px; border-collapse: separate; margin-left: -15px; }}
            .feature-card {{ display: table-cell; width: 50%; background: #0f172a; padding: 20px; border-radius: 12px; border: 1px solid #1e293b; text-align: center; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }}
            .feature-title {{ color: #e2e8f0; font-size: 15px; font-weight: 600; margin: 0 0 8px 0; }}
            .feature-desc {{ color: #94a3b8; font-size: 13px; margin: 0; line-height: 1.5; }}
            
            .cta-container {{ text-align: center; margin: 40px 0 10px 0; }}
            .cta-btn {{ display: inline-block; background: linear-gradient(135deg, #3b82f6, #10b981); color: #ffffff !important; padding: 16px 36px; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px; letter-spacing: 0.5px; box-shadow: 0 4px 14px rgba(59, 130, 246, 0.3); text-transform: uppercase; }}
            
            .footer {{ background: #0f172a; padding: 25px; text-align: center; border-top: 1px solid #334155; }}
            .footer p {{ color: #64748b; font-size: 12px; margin: 5px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Analysis Complete</h1>
                <p>Your Intelligence Report is ready for review.</p>
            </div>
            
            <div class="content">
                <p class="greeting">Hello <strong>{username}</strong>,</p>
                <p style="font-size: 16px; line-height: 1.6;">Precise AI has finished compiling the comprehensive analytical report for your uploaded ledger. The results have been formatted into an interactive dashboard.</p>
                
                <div class="meta-box">
                    <p class="meta-label">Source Document</p>
                    <p class="meta-value">{filename}</p>
                </div>
                
                <div class="grid">
                    <div class="feature-card">
                        <p class="feature-title">Interactive Visuals</p>
                        <p class="feature-desc">Dynamic Chart.js rendering mapped to browser arrays.</p>
                    </div>
                    <div class="feature-card">
                        <p class="feature-title">PDF Export Attached</p>
                        <p class="feature-desc">A securely compiled PDF snapshot is bolted directly to this email.</p>
                    </div>
                </div>
                
                <div class="cta-container">
                    <a href="http://localhost:8000/app" class="cta-btn">Access Dashboard</a>
                </div>
            </div>
            
            <div class="footer">
                <p>This report was generated automatically via Precise AI Neural Extraction.</p>
                <p>Do not reply to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """
    await send_html_email(to_email, f"Report Ready: {filename}", html_content, pdf_buffer, f"Precise_AI_Report_{filename}.pdf")
