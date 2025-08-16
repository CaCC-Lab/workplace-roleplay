#!/usr/bin/env python3
"""
🏥 Comprehensive Health Check System for Workplace Roleplay
Multi-dimensional health monitoring with detailed reporting
"""

import argparse
import asyncio
import aiohttp
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import psutil
import subprocess


class HealthMetrics:
    """Health metrics collection and analysis"""
    
    def __init__(self):
        self.metrics = {}
        self.start_time = time.time()
    
    def add_metric(self, category: str, name: str, value: any, status: str = "ok"):
        """Add a health metric"""
        if category not in self.metrics:
            self.metrics[category] = {}
        
        self.metrics[category][name] = {
            'value': value,
            'status': status,
            'timestamp': time.time()
        }
    
    def get_overall_status(self) -> str:
        """Calculate overall health status"""
        failed_checks = 0
        warning_checks = 0
        total_checks = 0
        
        for category in self.metrics.values():
            for metric in category.values():
                total_checks += 1
                if metric['status'] == 'failed':
                    failed_checks += 1
                elif metric['status'] == 'warning':
                    warning_checks += 1
        
        if failed_checks > 0:
            return 'unhealthy'
        elif warning_checks > 0:
            return 'degraded'
        else:
            return 'healthy'
    
    def to_dict(self) -> Dict:
        """Convert metrics to dictionary for JSON serialization"""
        return {
            'overall_status': self.get_overall_status(),
            'check_duration': time.time() - self.start_time,
            'timestamp': datetime.now().isoformat(),
            'metrics': self.metrics
        }


class SystemHealthChecker:
    """System-level health checks"""
    
    @staticmethod
    def check_cpu_usage() -> Tuple[float, str]:
        """Check CPU usage"""
        cpu_percent = psutil.cpu_percent(interval=1)
        
        if cpu_percent > 90:
            return cpu_percent, 'failed'
        elif cpu_percent > 70:
            return cpu_percent, 'warning'
        else:
            return cpu_percent, 'ok'
    
    @staticmethod
    def check_memory_usage() -> Tuple[Dict, str]:
        """Check memory usage"""
        memory = psutil.virtual_memory()
        memory_info = {
            'total': memory.total,
            'available': memory.available,
            'percent': memory.percent,
            'used': memory.used
        }
        
        if memory.percent > 90:
            return memory_info, 'failed'
        elif memory.percent > 80:
            return memory_info, 'warning'
        else:
            return memory_info, 'ok'
    
    @staticmethod
    def check_disk_usage(path: str = '/opt/workplace-app') -> Tuple[Dict, str]:
        """Check disk usage"""
        disk = psutil.disk_usage(path)
        disk_info = {
            'total': disk.total,
            'used': disk.used,
            'free': disk.free,
            'percent': (disk.used / disk.total) * 100
        }
        
        if disk_info['percent'] > 90:
            return disk_info, 'failed'
        elif disk_info['percent'] > 80:
            return disk_info, 'warning'
        else:
            return disk_info, 'ok'
    
    @staticmethod
    def check_load_average() -> Tuple[List[float], str]:
        """Check system load average"""
        load_avg = psutil.getloadavg()
        cpu_count = psutil.cpu_count()
        
        # Normalize load average by CPU count
        normalized_load = load_avg[0] / cpu_count
        
        if normalized_load > 2.0:
            return list(load_avg), 'failed'
        elif normalized_load > 1.5:
            return list(load_avg), 'warning'
        else:
            return list(load_avg), 'ok'


class ApplicationHealthChecker:
    """Application-specific health checks"""
    
    def __init__(self, base_url: str = "https://workplace-roleplay.cacc-lab.net"):
        self.base_url = base_url
    
    async def check_service_status(self) -> Tuple[Dict, str]:
        """Check systemd service status"""
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', 'workplace-app'],
                capture_output=True,
                text=True
            )
            
            is_active = result.stdout.strip() == 'active'
            
            # Get detailed service info
            result_status = subprocess.run(
                ['systemctl', 'status', 'workplace-app', '--no-pager', '-l'],
                capture_output=True,
                text=True
            )
            
            service_info = {
                'active': is_active,
                'status_output': result_status.stdout if result_status.returncode == 0 else result_status.stderr
            }
            
            return service_info, 'ok' if is_active else 'failed'
            
        except Exception as e:
            return {'error': str(e)}, 'failed'
    
    async def check_http_endpoints(self) -> Tuple[Dict, str]:
        """Check critical HTTP endpoints"""
        endpoints = {
            'health': '/health',
            'api_models': '/api/models',
            'main_page': '/',
            'scenarios': '/scenarios'
        }
        
        results = {}
        overall_status = 'ok'
        
        async with aiohttp.ClientSession() as session:
            for name, endpoint in endpoints.items():
                try:
                    url = f"{self.base_url}{endpoint}"
                    start_time = time.time()
                    
                    async with session.get(url, timeout=10) as response:
                        response_time = time.time() - start_time
                        
                        results[name] = {
                            'url': url,
                            'status_code': response.status,
                            'response_time': response_time,
                            'healthy': response.status == 200
                        }
                        
                        if response.status != 200:
                            overall_status = 'failed'
                        elif response_time > 2.0:
                            overall_status = 'warning' if overall_status == 'ok' else overall_status
                            
                except asyncio.TimeoutError:
                    results[name] = {
                        'url': f"{self.base_url}{endpoint}",
                        'error': 'timeout',
                        'healthy': False
                    }
                    overall_status = 'failed'
                    
                except Exception as e:
                    results[name] = {
                        'url': f"{self.base_url}{endpoint}",
                        'error': str(e),
                        'healthy': False
                    }
                    overall_status = 'failed'
        
        return results, overall_status
    
    async def check_ssl_certificate(self) -> Tuple[Dict, str]:
        """Check SSL certificate validity"""
        try:
            import ssl
            import socket
            from urllib.parse import urlparse
            
            parsed_url = urlparse(self.base_url)
            hostname = parsed_url.hostname
            port = parsed_url.port or 443
            
            context = ssl.create_default_context()
            with socket.create_connection((hostname, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    
                    # Parse certificate dates
                    not_after = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                    not_before = datetime.strptime(cert['notBefore'], '%b %d %H:%M:%S %Y %Z')
                    now = datetime.now()
                    
                    days_until_expiry = (not_after - now).days
                    
                    cert_info = {
                        'subject': cert['subject'],
                        'issuer': cert['issuer'],
                        'not_before': not_before.isoformat(),
                        'not_after': not_after.isoformat(),
                        'days_until_expiry': days_until_expiry,
                        'san': cert.get('subjectAltName', [])
                    }
                    
                    if days_until_expiry < 7:
                        return cert_info, 'failed'
                    elif days_until_expiry < 30:
                        return cert_info, 'warning'
                    else:
                        return cert_info, 'ok'
                        
        except Exception as e:
            return {'error': str(e)}, 'failed'
    
    async def check_application_logs(self) -> Tuple[Dict, str]:
        """Check application logs for errors"""
        log_paths = [
            '/opt/workplace-app/shared/logs/error.log',
            '/var/log/nginx/workplace-roleplay-error.log'
        ]
        
        log_analysis = {}
        overall_status = 'ok'
        
        for log_path in log_paths:
            try:
                log_file = Path(log_path)
                if not log_file.exists():
                    continue
                
                # Check last 100 lines for recent errors
                result = subprocess.run(
                    ['tail', '-100', str(log_file)],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    recent_errors = [line for line in lines if 'ERROR' in line.upper()]
                    
                    log_analysis[log_path] = {
                        'exists': True,
                        'recent_error_count': len(recent_errors),
                        'recent_errors': recent_errors[-5:] if recent_errors else []  # Last 5 errors
                    }
                    
                    if len(recent_errors) > 10:
                        overall_status = 'failed'
                    elif len(recent_errors) > 5:
                        overall_status = 'warning' if overall_status == 'ok' else overall_status
                        
            except Exception as e:
                log_analysis[log_path] = {
                    'exists': False,
                    'error': str(e)
                }
        
        return log_analysis, overall_status


class ComprehensiveHealthChecker:
    """Main health checker orchestrator"""
    
    def __init__(self, base_url: str = "https://workplace-roleplay.cacc-lab.net"):
        self.base_url = base_url
        self.system_checker = SystemHealthChecker()
        self.app_checker = ApplicationHealthChecker(base_url)
        self.metrics = HealthMetrics()
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)
    
    async def run_all_checks(self) -> Dict:
        """Run all health checks"""
        self.logger.info("🏥 Starting comprehensive health check...")
        
        # System checks
        await self._run_system_checks()
        
        # Application checks
        await self._run_application_checks()
        
        # Generate report
        report = self.metrics.to_dict()
        
        self.logger.info(f"✅ Health check completed - Status: {report['overall_status']}")
        return report
    
    async def _run_system_checks(self):
        """Run system-level health checks"""
        self.logger.info("🔧 Running system health checks...")
        
        # CPU usage
        cpu_usage, cpu_status = self.system_checker.check_cpu_usage()
        self.metrics.add_metric('system', 'cpu_usage_percent', cpu_usage, cpu_status)
        
        # Memory usage
        memory_info, memory_status = self.system_checker.check_memory_usage()
        self.metrics.add_metric('system', 'memory_usage', memory_info, memory_status)
        
        # Disk usage
        disk_info, disk_status = self.system_checker.check_disk_usage()
        self.metrics.add_metric('system', 'disk_usage', disk_info, disk_status)
        
        # Load average
        load_avg, load_status = self.system_checker.check_load_average()
        self.metrics.add_metric('system', 'load_average', load_avg, load_status)
    
    async def _run_application_checks(self):
        """Run application-specific health checks"""
        self.logger.info("🚀 Running application health checks...")
        
        # Service status
        service_info, service_status = await self.app_checker.check_service_status()
        self.metrics.add_metric('application', 'service_status', service_info, service_status)
        
        # HTTP endpoints
        endpoint_results, endpoint_status = await self.app_checker.check_http_endpoints()
        self.metrics.add_metric('application', 'http_endpoints', endpoint_results, endpoint_status)
        
        # SSL certificate
        ssl_info, ssl_status = await self.app_checker.check_ssl_certificate()
        self.metrics.add_metric('security', 'ssl_certificate', ssl_info, ssl_status)
        
        # Application logs
        log_analysis, log_status = await self.app_checker.check_application_logs()
        self.metrics.add_metric('application', 'log_analysis', log_analysis, log_status)


async def main():
    """Main health check function"""
    parser = argparse.ArgumentParser(description='Workplace Roleplay Health Checker')
    parser.add_argument('--url', default='https://workplace-roleplay.cacc-lab.net', help='Base URL to check')
    parser.add_argument('--output', choices=['json', 'human'], default='human', help='Output format')
    parser.add_argument('--output-file', help='Output file path (JSON format)')
    parser.add_argument('--exit-code', action='store_true', help='Exit with non-zero code if unhealthy')
    
    args = parser.parse_args()
    
    # Run health checks
    checker = ComprehensiveHealthChecker(args.url)
    report = await checker.run_all_checks()
    
    # Output results
    if args.output == 'json':
        json_output = json.dumps(report, indent=2, default=str)
        print(json_output)
        
        if args.output_file:
            with open(args.output_file, 'w') as f:
                f.write(json_output)
    else:
        # Human-readable output
        print(f"\n🏥 Health Check Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        print(f"Overall Status: {report['overall_status'].upper()}")
        print(f"Check Duration: {report['check_duration']:.2f}s")
        print()
        
        for category, metrics in report['metrics'].items():
            print(f"📊 {category.upper()}")
            print("-" * 40)
            
            for metric_name, metric_data in metrics.items():
                status_emoji = {
                    'ok': '✅',
                    'warning': '⚠️',
                    'failed': '❌'
                }.get(metric_data['status'], '❓')
                
                print(f"  {status_emoji} {metric_name}: {metric_data['status']}")
                
                # Show key metric values
                if isinstance(metric_data['value'], dict):
                    for key, value in metric_data['value'].items():
                        if key in ['percent', 'response_time', 'days_until_expiry', 'recent_error_count']:
                            print(f"    {key}: {value}")
                elif isinstance(metric_data['value'], (int, float)):
                    print(f"    value: {metric_data['value']}")
            print()
    
    # Exit with appropriate code
    if args.exit_code:
        if report['overall_status'] == 'healthy':
            sys.exit(0)
        elif report['overall_status'] == 'degraded':
            sys.exit(1)
        else:  # unhealthy
            sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())