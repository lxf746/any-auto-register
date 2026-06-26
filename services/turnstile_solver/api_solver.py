import os
import sys
import time
import uuid
import random
import logging
import asyncio
from typing import Optional, Union
import argparse
from quart import Quart, request, jsonify
from camoufox.async_api import AsyncCamoufox
from patchright.async_api import async_playwright
from db_results import init_db, save_result, load_result, cleanup_old_results
from browser_configs import browser_config
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich import box



COLORS = {
    'MAGENTA': '\033[35m',
    'BLUE': '\033[34m',
    'GREEN': '\033[32m',
    'YELLOW': '\033[33m',
    'RED': '\033[31m',
    'RESET': '\033[0m',
}


class CustomLogger(logging.Logger):
    @staticmethod
    def format_message(level, color, message):
        timestamp = time.strftime('%H:%M:%S')
        return f"[{timestamp}] [{COLORS.get(color)}{level}{COLORS.get('RESET')}] -> {message}"

    def debug(self, message, *args, **kwargs):
        super().debug(self.format_message('DEBUG', 'MAGENTA', message), *args, **kwargs)

    def info(self, message, *args, **kwargs):
        super().info(self.format_message('INFO', 'BLUE', message), *args, **kwargs)

    def success(self, message, *args, **kwargs):
        super().info(self.format_message('SUCCESS', 'GREEN', message), *args, **kwargs)

    def warning(self, message, *args, **kwargs):
        super().warning(self.format_message('WARNING', 'YELLOW', message), *args, **kwargs)

    def error(self, message, *args, **kwargs):
        super().error(self.format_message('ERROR', 'RED', message), *args, **kwargs)


logging.setLoggerClass(CustomLogger)
logger: CustomLogger = logging.getLogger("TurnstileAPIServer")  # type: ignore
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)


class TurnstileAPIServer:

    def __init__(self, headless: bool, useragent: Optional[str], debug: bool, browser_type: str, thread: int, proxy_support: bool, use_random_config: bool = False, browser_name: Optional[str] = None, browser_version: Optional[str] = None):
        self.app = Quart(__name__)
        self.debug = debug
        self.browser_type = browser_type
        self.headless = headless
        self.thread_count = thread
        self.proxy_support = proxy_support
        self.browser_pool = asyncio.Queue()
        self.use_random_config = use_random_config
        self.browser_name = browser_name
        self.browser_version = browser_version
        self.console = Console()
        
        # Initialize useragent and sec_ch_ua attributes
        self.useragent = useragent
        self.sec_ch_ua = None
        
        
        if self.browser_type in ['chromium', 'chrome', 'msedge']:
            if browser_name and browser_version:
                config = browser_config.get_browser_config(browser_name, browser_version)
                if config:
                    useragent, sec_ch_ua = config
                    self.useragent = useragent
                    self.sec_ch_ua = sec_ch_ua
            elif useragent:
                self.useragent = useragent
            else:
                browser, version, useragent, sec_ch_ua = browser_config.get_random_browser_config(self.browser_type)
                self.browser_name = browser
                self.browser_version = version
                self.useragent = useragent
                self.sec_ch_ua = sec_ch_ua
        
        self.browser_args = []
        if self.useragent:
            self.browser_args.append(f"--user-agent={self.useragent}")

        self._setup_routes()

    def display_welcome(self):
        """Displays welcome screen with logo."""
        self.console.clear()
        
        combined_text = Text()
        combined_text.append("\n📢 Channel: ", style="bold white")
        combined_text.append("https://t.me/D3_vin", style="cyan")
        combined_text.append("\n💬 Chat: ", style="bold white")
        combined_text.append("https://t.me/D3vin_chat", style="cyan")
        combined_text.append("\n📁 GitHub: ", style="bold white")
        combined_text.append("https://github.com/D3-vin", style="cyan")
        combined_text.append("\n📁 Version: ", style="bold white")
        combined_text.append("1.2a", style="green")
        combined_text.append("\n")

        info_panel = Panel(
            Align.left(combined_text),
            title="[bold blue]Turnstile Solver[/bold blue]",
            subtitle="[bold magenta]Dev by D3vin[/bold magenta]",
            box=box.ROUNDED,
            border_style="bright_blue",
            padding=(0, 1),
            width=50
        )

        self.console.print(info_panel)
        self.console.print()




    def _setup_routes(self) -> None:
        """Set up the application routes."""
        self.app.before_serving(self._startup)
        self.app.route('/turnstile', methods=['GET'])(self.process_turnstile)
        self.app.route('/result', methods=['GET'])(self.get_result)
        self.app.route('/')(self.index)
        

    async def _startup(self) -> None:
        """Initialize the browser and page pool on startup."""
        self.display_welcome()
        logger.info("Starting browser initialization")
        try:
            await init_db()
            await self._initialize_browser()
            
            # Start periodic cleanup of old results
            asyncio.create_task(self._periodic_cleanup())
            
        except Exception as e:
            logger.error(f"Failed to initialize browser: {str(e)}")
            raise

    async def _initialize_browser(self) -> None:
        """Initialize the browser and create the page pool."""
        playwright = None
        camoufox = None

        if self.browser_type in ['chromium', 'chrome', 'msedge']:
            playwright = await async_playwright().start()
        elif self.browser_type == "camoufox":
            camoufox = AsyncCamoufox(headless=self.headless)

        browser_configs = []
        for _ in range(self.thread_count):
            if self.browser_type in ['chromium', 'chrome', 'msedge']:
                if self.use_random_config:
                    browser, version, useragent, sec_ch_ua = browser_config.get_random_browser_config(self.browser_type)
                elif self.browser_name and self.browser_version:
                    config = browser_config.get_browser_config(self.browser_name, self.browser_version)
                    if config:
                        useragent, sec_ch_ua = config
                        browser = self.browser_name
                        version = self.browser_version
                    else:
                        browser, version, useragent, sec_ch_ua = browser_config.get_random_browser_config(self.browser_type)
                else:
                    browser = getattr(self, 'browser_name', 'custom')
                    version = getattr(self, 'browser_version', 'custom')
                    useragent = self.useragent
                    sec_ch_ua = getattr(self, 'sec_ch_ua', '')
            else:
                # For camoufox and other browsers use default values
                browser = self.browser_type
                version = 'custom'
                useragent = self.useragent
                sec_ch_ua = getattr(self, 'sec_ch_ua', '')

            
            browser_configs.append({
                'browser_name': browser,
                'browser_version': version,
                'useragent': useragent,
                'sec_ch_ua': sec_ch_ua
            })

        for i in range(self.thread_count):
            config = browser_configs[i]
            
            browser_args = [
                "--window-position=0,0",
                "--force-device-scale-factor=1"
            ]
            if config['useragent']:
                browser_args.append(f"--user-agent={config['useragent']}")
            
            browser = None
            if self.browser_type in ['chromium', 'chrome', 'msedge'] and playwright:
                browser = await playwright.chromium.launch(
                    channel=self.browser_type,
                    headless=self.headless,
                    args=browser_args
                )
            elif self.browser_type == "camoufox" and camoufox:
                browser = await camoufox.start()

            if browser:
                await self.browser_pool.put((i+1, browser, config))

            if self.debug:
                logger.info(f"Browser {i + 1} initialized successfully with {config['browser_name']} {config['browser_version']}")

        logger.info(f"Browser pool initialized with {self.browser_pool.qsize()} browsers")
        
        if self.use_random_config:
            logger.info(f"Each browser in pool received random configuration")
        elif self.browser_name and self.browser_version:
            logger.info(f"All browsers using configuration: {self.browser_name} {self.browser_version}")
        else:
            logger.info("Using custom configuration")
            
        if self.debug:
            for i, config in enumerate(browser_configs):
                logger.debug(f"Browser {i+1} config: {config['browser_name']} {config['browser_version']}")
                logger.debug(f"Browser {i+1} User-Agent: {config['useragent']}")
                logger.debug(f"Browser {i+1} Sec-CH-UA: {config['sec_ch_ua']}")

    async def _periodic_cleanup(self):
        """Periodic cleanup of old results every hour"""
        while True:
            try:
                await asyncio.sleep(3600)
                deleted_count = await cleanup_old_results(days_old=7)
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old results")
            except Exception as e:
                logger.error(f"Error during periodic cleanup: {e}")

    async def _antishadow_inject(self, page):
        await page.add_init_script("""
          (function() {
            const originalAttachShadow = Element.prototype.attachShadow;
            Element.prototype.attachShadow = function(init) {
              const shadow = originalAttachShadow.call(this, init);
              if (init.mode === 'closed') {
                window.__lastClosedShadowRoot = shadow;
              }
              return shadow;
            };
          })();
        """)



    async def _optimized_route_handler(self, route):
        """Optimized route handler to save resources."""
        url = route.request.url
        resource_type = route.request.resource_type

        allowed_types = {'document', 'script', 'xhr', 'fetch', 'stylesheet'}

        allowed_domains = [
            'challenges.cloudflare.com',
            'static.cloudflareinsights.com',
            'cloudflare.com',
        ]

        blocked_types = {'media', 'font', 'websocket', 'eventsource', 'manifest'}
        blocked_domains = [
            'sentry.io',
            'google-analytics.com',
            'googletagmanager.com',
            'ads.linkedin.com',
            'px.ads.linkedin.com',
        ]

        if any(domain in url for domain in blocked_domains):
            await route.abort()
        elif resource_type in blocked_types:
            await route.abort()
        elif resource_type in allowed_types:
            await route.continue_()
        elif any(domain in url for domain in allowed_domains):
            await route.continue_()
        elif resource_type == 'image':
            await route.abort()
        else:
            await route.continue_()

    async def _block_rendering(self, page):
        """Block rendering to save resources"""
        await page.route("**/*", self._optimized_route_handler)

    async def _unblock_rendering(self, page):
        """Unblock rendering"""
        await page.unroute("**/*", self._optimized_route_handler)

    async def _find_turnstile_elements(self, page, index: int):
        """Smart check for all possible Turnstile elements"""
        selectors = [
            '.cf-turnstile',
            '[data-sitekey]',
            'iframe[src*="turnstile"]',
            'iframe[title*="widget"]',
            'div[id*="turnstile"]',
            'div[class*="turnstile"]'
        ]
        
        elements = []
        for selector in selectors:
            try:
                # Safe count() check
                try:
                    count = await page.locator(selector).count()
                except Exception:
                    # If count() throws an error, skip this selector
                    continue
                    
                if count > 0:
                    elements.append((selector, count))
                    if self.debug:
                        logger.debug(f"Browser {index}: Found {count} elements with selector '{selector}'")
            except Exception as e:
                if self.debug:
                    logger.debug(f"Browser {index}: Selector '{selector}' failed: {str(e)}")
                continue
        
        return elements

    async def _find_and_click_checkbox(self, page, index: int):
        """Find and click the Turnstile CAPTCHA checkbox inside iframe"""
        try:
            # Try different iframe selectors with error protection
            iframe_selectors = [
                'iframe[src*="challenges.cloudflare.com"]',
                'iframe[src*="turnstile"]',
                'iframe[title*="widget"]'
            ]
            
            iframe_locator = None
            for selector in iframe_selectors:
                try:
                    test_locator = page.locator(selector).first
                    # Safe count check for iframe
                    try:
                        iframe_count = await test_locator.count()
                    except Exception:
                        iframe_count = 0
                        
                    if iframe_count > 0:
                        iframe_locator = test_locator
                        if self.debug:
                            logger.debug(f"Browser {index}: Found Turnstile iframe with selector: {selector}")
                        break
                except Exception as e:
                    if self.debug:
                        logger.debug(f"Browser {index}: Iframe selector '{selector}' failed: {str(e)}")
                    continue
            
            if iframe_locator:
                try:
                    # Get frame from iframe
                    iframe_element = await iframe_locator.element_handle()
                    frame = await iframe_element.content_frame()
                    
                    if frame:
                        # Look for checkbox inside iframe
                        checkbox_selectors = [
                            'input[type="checkbox"]',
                            '.cb-lb input[type="checkbox"]',
                            'label input[type="checkbox"]'
                        ]
                        
                        for selector in checkbox_selectors:
                            try:
                                # Completely avoid locator.count() in iframe - use alternative approach
                                try:
                                    # Try direct click without count check
                                    checkbox = frame.locator(selector).first
                                    await checkbox.click(timeout=2000)
                                    if self.debug:
                                        logger.debug(f"Browser {index}: Successfully clicked checkbox in iframe with selector '{selector}'")
                                    return True
                                except Exception as click_e:
                                    # If direct click didn't work, log to debug but don't crash
                                    if self.debug:
                                        logger.debug(f"Browser {index}: Direct checkbox click failed for '{selector}': {str(click_e)}")
                                    continue
                            except Exception as e:
                                if self.debug:
                                    logger.debug(f"Browser {index}: Iframe checkbox selector '{selector}' failed: {str(e)}")
                                continue
                    
                        # If iframe found but checkbox click failed, try clicking iframe directly
                        try:
                            if self.debug:
                                logger.debug(f"Browser {index}: Trying to click iframe directly as fallback")
                            await iframe_locator.click(timeout=1000)
                            return True
                        except Exception as e:
                            if self.debug:
                                logger.debug(f"Browser {index}: Iframe direct click failed: {str(e)}")
                
                except Exception as e:
                    if self.debug:
                        logger.debug(f"Browser {index}: Failed to access iframe content: {str(e)}")
            
        except Exception as e:
            if self.debug:
                logger.debug(f"Browser {index}: General iframe search failed: {str(e)}")
        
        return False

    async def _try_click_strategies(self, page, index: int):
        strategies = [
            ('checkbox_click', lambda: self._find_and_click_checkbox(page, index)),
            ('direct_widget', lambda: self._safe_click(page, '.cf-turnstile', index)),
            ('iframe_click', lambda: self._safe_click(page, 'iframe[src*="turnstile"]', index)),
            ('js_click', lambda: page.evaluate("document.querySelector('.cf-turnstile')?.click()")),
            ('sitekey_attr', lambda: self._safe_click(page, '[data-sitekey]', index)),
            ('any_turnstile', lambda: self._safe_click(page, '*[class*="turnstile"]', index)),
            ('xpath_click', lambda: self._safe_click(page, "//div[@class='cf-turnstile']", index))
        ]
        
        for strategy_name, strategy_func in strategies:
            try:
                result = await strategy_func()
                if result is True or result is None:  # None means success for most strategies
                    if self.debug:
                        logger.debug(f"Browser {index}: Click strategy '{strategy_name}' succeeded")
                    return True
            except Exception as e:
                if self.debug:
                    logger.debug(f"Browser {index}: Click strategy '{strategy_name}' failed: {str(e)}")
                continue
        
        return False

    async def _safe_click(self, page, selector: str, index: int):
        """Fully safe click with maximum error protection"""
        try:
            # Try direct click without count() check
            locator = page.locator(selector).first
            await locator.click(timeout=1000)
            return True
        except Exception as e:
            # Log error only in debug mode
            if self.debug and "Can't query n-th element" not in str(e):
                logger.debug(f"Browser {index}: Safe click failed for '{selector}': {str(e)}")
            return False

    async def _inject_captcha_directly(self, page, websiteKey: str, action: str = '', cdata: str = '', index: int = 0):
        """Inject CAPTCHA directly into the target website or use existing one"""
        script = f"""
        (function() {{
        // Check if there's already a turnstile widget on the page with matching sitekey
        const existingWidgets = document.querySelectorAll('.cf-turnstile, [data-sitekey]');
        console.log('Turnstile Debug: Found ' + existingWidgets.length + ' potential widgets');
        let useExisting = false;
        let foundSitekey = null;
        
        for (const widget of existingWidgets) {{
            const widgetSitekey = widget.getAttribute('data-sitekey');
            console.log('Turnstile Debug: Checking widget with sitekey:', widgetSitekey);
            if (widgetSitekey === '{websiteKey}') {{
                useExisting = true;
                foundSitekey = widgetSitekey;
                console.log('Turnstile Debug: Found existing turnstile widget with matching sitekey');
                break;
            }}
        }}
        
        // Also check for iframe-based turnstile
        const turnstileIframes = document.querySelectorAll('iframe[src*="turnstile"], iframe[src*="challenges.cloudflare"]');
        console.log('Turnstile Debug: Found ' + turnstileIframes.length + ' turnstile iframes');
        
        // Create hidden input for token if not exists
        let tokenInput = document.querySelector('input[name="cf-turnstile-response"]');
        if (!tokenInput) {{
            tokenInput = document.createElement('input');
            tokenInput.type = 'hidden';
            tokenInput.name = 'cf-turnstile-response';
            document.body.appendChild(tokenInput);
        }}
        
        // Setup token capture callback
        window._turnstileTokenCallback = function(token) {{
            console.log('Turnstile token captured:', token);
            tokenInput.value = token;
        }};
        
        // If existing widget found, try to hook into it
        if (useExisting) {{
            console.log('Using existing turnstile widget');
            // Try to override the existing callback or add our own
            const originalCallback = window.turnstileCallback;
            window.turnstileCallback = function(token) {{
                window._turnstileTokenCallback(token);
                if (originalCallback) originalCallback(token);
            }};
            // Also try to set up a mutation observer to capture token changes
            return 'existing';
        }}
        
        // Remove any existing turnstile widgets that don't match our sitekey
        document.querySelectorAll('.cf-turnstile').forEach(el => el.remove());
        document.querySelectorAll('[data-sitekey]').forEach(el => {{
            if (el.getAttribute('data-sitekey') !== '{websiteKey}') el.remove();
        }});
        
        // Create turnstile widget directly on the page
        const captchaDiv = document.createElement('div');
        captchaDiv.className = 'cf-turnstile';
        captchaDiv.setAttribute('data-sitekey', '{websiteKey}');
        captchaDiv.setAttribute('data-callback', '_turnstileTokenCallback');
        {f'captchaDiv.setAttribute("data-action", "{action}");' if action else ''}
        {f'captchaDiv.setAttribute("data-cdata", "{cdata}");' if cdata else ''}
        captchaDiv.style.position = 'fixed';
        captchaDiv.style.top = '20px';
        captchaDiv.style.left = '20px';
        captchaDiv.style.zIndex = '9999';
        captchaDiv.style.backgroundColor = 'white';
        captchaDiv.style.padding = '15px';
        captchaDiv.style.border = '2px solid #0f79af';
        captchaDiv.style.borderRadius = '8px';
        captchaDiv.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.3)';
        
        // Add to body immediately
        document.body.appendChild(captchaDiv);
        
        // Load Turnstile script and render widget
        const loadTurnstile = () => {{
            const script = document.createElement('script');
            script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js';
            script.async = true;
            script.defer = true;
            script.onload = function() {{
                console.log('Turnstile script loaded');
                // Wait a bit for script to initialize
                setTimeout(() => {{
                    if (window.turnstile && window.turnstile.render) {{
                        try {{
                            window.turnstile.render(captchaDiv, {{
                                sitekey: '{websiteKey}',
                                {f'action: "{action}",' if action else ''}
                                {f'cdata: "{cdata}",' if cdata else ''}
                                callback: function(token) {{
                                    console.log('Turnstile solved with token:', token);
                                    window._turnstileTokenCallback(token);
                                }},
                                'error-callback': function(error) {{
                                    console.log('Turnstile error:', error);
                                }}
                            }});
                        }} catch (e) {{
                            console.log('Turnstile render error:', e);
                        }}
                    }} else {{
                        console.log('Turnstile API not available');
                    }}
                }}, 1000);
            }};
            script.onerror = function() {{
                console.log('Failed to load Turnstile script');
            }};
            document.head.appendChild(script);
        }};
        
        // Check if Turnstile is already loaded
        if (window.turnstile) {{
            console.log('Turnstile already loaded, rendering immediately');
            try {{
                window.turnstile.render(captchaDiv, {{
                    sitekey: '{websiteKey}',
                    {f'action: "{action}",' if action else ''}
                    {f'cdata: "{cdata}",' if cdata else ''}
                    callback: function(token) {{
                        console.log('Turnstile solved with token:', token);
                        window._turnstileTokenCallback(token);
                    }},
                    'error-callback': function(error) {{
                        console.log('Turnstile error:', error);
                    }}
                }});
            }} catch (e) {{
                console.log('Immediate render error:', e);
                loadTurnstile();
            }}
        }} else {{
            loadTurnstile();
        }}
        
        // Setup global callback
        window.onTurnstileCallback = function(token) {{
            console.log('Global turnstile callback executed:', token);
        }};
        
        return 'injected';
        }})();
        """

        result = await page.evaluate(script)
        if self.debug:
            if result == 'existing':
                logger.debug(f"Browser {index}: Detected existing turnstile widget with matching sitekey")
            else:
                logger.debug(f"Browser {index}: Injected new CAPTCHA widget with sitekey: {websiteKey}")
        return result

    async def _solve_turnstile(self, task_id: str, url: str, sitekey: str, action: Optional[str] = None, cdata: Optional[str] = None):
        """Solve the Turnstile challenge."""
        proxy = None

        index, browser, browser_config = await self.browser_pool.get()
        context = None

        try:
            if hasattr(browser, 'is_connected') and not browser.is_connected():
                if self.debug:
                    logger.warning(f"Browser {index}: Browser disconnected, skipping")
                await self.browser_pool.put((index, browser, browser_config))
                await save_result(task_id, "turnstile", {"value": "CAPTCHA_FAIL", "elapsed_time": 0})
                return
        except Exception as e:
            if self.debug:
                logger.warning(f"Browser {index}: Cannot check browser state: {str(e)}")

        if self.proxy_support:
            proxy_file_path = os.path.join(os.getcwd(), "proxies.txt")

            try:
                with open(proxy_file_path) as proxy_file:
                    proxies = [line.strip() for line in proxy_file if line.strip()]

                proxy = random.choice(proxies) if proxies else None
                
                if self.debug and proxy:
                    logger.debug(f"Browser {index}: Selected proxy: {proxy}")
                elif self.debug and not proxy:
                    logger.debug(f"Browser {index}: No proxies available")
                    
            except FileNotFoundError:
                logger.warning(f"Proxy file not found: {proxy_file_path}")
                proxy = None
            except Exception as e:
                logger.error(f"Error reading proxy file: {str(e)}")
                proxy = None

            if proxy:
                if '@' in proxy:
                    try:
                        scheme_part, auth_part = proxy.split('://')
                        auth, address = auth_part.split('@')
                        username, password = auth.split(':')
                        ip, port = address.split(':')
                        if self.debug:
                            logger.debug(f"Browser {index}: Creating context with proxy {scheme_part}://{ip}:{port} (auth: {username}:***)")
                        context_options = {
                            "proxy": {
                                "server": f"{scheme_part}://{ip}:{port}",
                                "username": username,
                                "password": password
                            },
                            "user_agent": browser_config['useragent']
                        }
                        
                        if browser_config['sec_ch_ua'] and browser_config['sec_ch_ua'].strip():
                            context_options['extra_http_headers'] = {
                                'sec-ch-ua': browser_config['sec_ch_ua']
                            }
                        
                        context = await browser.new_context(**context_options)
                    except ValueError:
                        raise ValueError(f"Invalid proxy format: {proxy}")
                else:
                    parts = proxy.split(':')
                    if len(parts) == 5:
                        proxy_scheme, proxy_ip, proxy_port, proxy_user, proxy_pass = parts
                        if self.debug:
                            logger.debug(f"Browser {index}: Creating context with proxy {proxy_scheme}://{proxy_ip}:{proxy_port} (auth: {proxy_user}:***)")
                        context_options = {
                            "proxy": {
                                "server": f"{proxy_scheme}://{proxy_ip}:{proxy_port}",
                                "username": proxy_user,
                                "password": proxy_pass
                            },
                            "user_agent": browser_config['useragent']
                        }
                        
                        if browser_config['sec_ch_ua'] and browser_config['sec_ch_ua'].strip():
                            context_options['extra_http_headers'] = {
                                'sec-ch-ua': browser_config['sec_ch_ua']
                            }
                        
                        context = await browser.new_context(**context_options)
                    elif len(parts) == 3:
                        if self.debug:
                            logger.debug(f"Browser {index}: Creating context with proxy {proxy}")
                        context_options = {
                            "proxy": {"server": f"{proxy}"},
                            "user_agent": browser_config['useragent']
                        }
                        
                        if browser_config['sec_ch_ua'] and browser_config['sec_ch_ua'].strip():
                            context_options['extra_http_headers'] = {
                                'sec-ch-ua': browser_config['sec_ch_ua']
                            }
                        
                        context = await browser.new_context(**context_options)
                    else:
                        raise ValueError(f"Invalid proxy format: {proxy}")
            else:
                if self.debug:
                    logger.debug(f"Browser {index}: Creating context without proxy")
                context_options = {"user_agent": browser_config['useragent']}
                
                if browser_config['sec_ch_ua'] and browser_config['sec_ch_ua'].strip():
                    context_options['extra_http_headers'] = {
                        'sec-ch-ua': browser_config['sec_ch_ua']
                    }
                
                context = await browser.new_context(**context_options)
        else:
            context_options = {"user_agent": browser_config['useragent']}
            
            if browser_config['sec_ch_ua'] and browser_config['sec_ch_ua'].strip():
                context_options['extra_http_headers'] = {
                    'sec-ch-ua': browser_config['sec_ch_ua']
                }
            
            context = await browser.new_context(**context_options)

        page = await context.new_page()
        
        await self._antishadow_inject(page)
        
        await self._block_rendering(page)
        
        await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
        
        window.chrome = {
            runtime: {},
            loadTimes: function() {},
            csi: function() {},
        };
        """)
        
        if self.browser_type in ['chromium', 'chrome', 'msedge']:
            await page.set_viewport_size({"width": 1280, "height": 720})
            if self.debug:
                logger.debug(f"Browser {index}: Set viewport size to 1280x720")

        start_time = time.time()

        try:
            if self.debug:
                logger.debug(f"Browser {index}: Starting Turnstile solve for URL: {url} with Sitekey: {sitekey} | Action: {action} | Cdata: {cdata} | Proxy: {proxy}")
                logger.debug(f"Browser {index}: Setting up optimized page loading with resource blocking")

            if self.debug:
                logger.debug(f"Browser {index}: Loading real website directly: {url}")

            await page.goto(url, wait_until='domcontentloaded', timeout=30000)

            await self._unblock_rendering(page)
            
            # Wait for turnstile to load (it may be lazy loaded)
            if self.debug:
                logger.debug(f"Browser {index}: Waiting for turnstile to appear...")
            
            # Try to wait for turnstile widget to appear
            turnstile_found = False
            for wait_attempt in range(15):
                widget_count = await page.locator('.cf-turnstile, [data-sitekey]').count()
                iframe_count = await page.locator('iframe[src*="turnstile"], iframe[src*="challenges.cloudflare"]').count()
                
                # Also check if turnstile API is available
                turnstile_ready = await page.evaluate("""() => {
                    return typeof window.turnstile !== 'undefined';
                }""")
                
                if self.debug and wait_attempt % 3 == 0:
                    logger.debug(f"Browser {index}: Wait {wait_attempt + 1}s - {widget_count} widgets, {iframe_count} iframes, turnstile API: {turnstile_ready}")
                
                if widget_count > 0 or iframe_count > 0 or turnstile_ready:
                    if self.debug:
                        logger.debug(f"Browser {index}: Turnstile ready after {wait_attempt + 1}s (widgets: {widget_count}, iframes: {iframe_count}, API: {turnstile_ready})")
                    turnstile_found = True
                    break
                await asyncio.sleep(1)
            
            if not turnstile_found:
                if self.debug:
                    logger.debug(f"Browser {index}: Turnstile not found naturally, will inject our own")
            
            # Immediately inject Turnstile widget into target site
            if self.debug:
                logger.debug(f"Browser {index}: Injecting Turnstile widget directly into target site")
            
            # Debug: Check page state before injection
            if self.debug:
                widget_count = await page.locator('.cf-turnstile, [data-sitekey]').count()
                iframe_count = await page.locator('iframe[src*="turnstile"], iframe[src*="challenges.cloudflare"]').count()
                logger.debug(f"Browser {index}: Before injection - {widget_count} widgets, {iframe_count} iframes")
                # Check for sitekey attribute
                try:
                    sitekey_elem = await page.locator('[data-sitekey]').get_attribute('data-sitekey')
                    logger.debug(f"Browser {index}: Found sitekey: {sitekey_elem}")
                except Exception:
                    pass
            
            inject_result = await self._inject_captcha_directly(page, sitekey, action or '', cdata or '', index)
            
            if self.debug:
                if inject_result == 'existing':
                    logger.debug(f"Browser {index}: Using existing turnstile widget on page")
                else:
                    logger.debug(f"Browser {index}: Injected new turnstile widget")
            
            # Wait for widget loading and rendering
            await asyncio.sleep(3)

            locator = page.locator('input[name="cf-turnstile-response"]')
            max_attempts = 30
            click_count = 0
            max_clicks = 10

            for attempt in range(max_attempts):
                try:
                    # Safe check of token element count
                    try:
                        count = await locator.count()
                    except Exception as e:
                        if self.debug:
                            logger.debug(f"Browser {index}: Locator count failed on attempt {attempt + 1}: {str(e)}")
                        count = 0

                    if count == 0:
                        if self.debug and attempt % 5 == 0:
                            logger.debug(f"Browser {index}: No token elements found on attempt {attempt + 1}")
                        # Also check if turnstile widget exists on page
                        if self.debug and attempt == 0:
                            widget_count = await page.locator('.cf-turnstile, [data-sitekey]').count()
                            iframe_count = await page.locator('iframe[src*="turnstile"], iframe[src*="challenges.cloudflare"]').count()
                            logger.debug(f"Browser {index}: Page has {widget_count} turnstile widgets and {iframe_count} iframes")
                    elif count == 1:
                        # If only one element, check its token
                        try:
                            token = await locator.input_value(timeout=500)
                            if token:
                                elapsed_time = round(time.time() - start_time, 3)
                                logger.success(f"Browser {index}: Successfully solved captcha - {COLORS.get('MAGENTA')}{token[:10]}{COLORS.get('RESET')} in {COLORS.get('GREEN')}{elapsed_time}{COLORS.get('RESET')} Seconds")
                                await save_result(task_id, "turnstile", {"value": token, "elapsed_time": elapsed_time})
                                return
                        except Exception as e:
                            if self.debug:
                                logger.debug(f"Browser {index}: Single token element check failed: {str(e)}")
                    else:
                        # If multiple elements, check them one by one
                        if self.debug:
                            logger.debug(f"Browser {index}: Found {count} token elements, checking all")

                        for i in range(count):
                            try:
                                element_token = await locator.nth(i).input_value(timeout=500)
                                if element_token:
                                    elapsed_time = round(time.time() - start_time, 3)
                                    logger.success(f"Browser {index}: Successfully solved captcha - {COLORS.get('MAGENTA')}{element_token[:10]}{COLORS.get('RESET')} in {COLORS.get('GREEN')}{elapsed_time}{COLORS.get('RESET')} Seconds")
                                    await save_result(task_id, "turnstile", {"value": element_token, "elapsed_time": elapsed_time})
                                    return
                            except Exception as e:
                                if self.debug:
                                    logger.debug(f"Browser {index}: Token element {i} check failed: {str(e)}")
                                continue

                    if attempt > 2 and attempt % 3 == 0 and click_count < max_clicks:
                        click_success = await self._try_click_strategies(page, index)
                        click_count += 1
                        if click_success and self.debug:
                            logger.debug(f"Browser {index}: Click successful (click #{click_count}/{max_clicks})")
                        elif not click_success and self.debug:
                            logger.debug(f"Browser {index}: All click strategies failed on attempt {attempt + 1} (click #{click_count}/{max_clicks})")

                    # Adaptive wait
                    wait_time = min(0.5 + (attempt * 0.05), 2.0)
                    await asyncio.sleep(wait_time)

                    if self.debug and attempt % 5 == 0:
                        logger.debug(f"Browser {index}: Attempt {attempt + 1}/{max_attempts} - Waiting for token (clicks: {click_count}/{max_clicks})")

                except Exception as e:
                    if self.debug:
                        logger.debug(f"Browser {index}: Attempt {attempt + 1} error: {str(e)}")
                    continue
            
            elapsed_time = round(time.time() - start_time, 3)
            await save_result(task_id, "turnstile", {"value": "CAPTCHA_FAIL", "elapsed_time": elapsed_time})
            if self.debug:
                logger.error(f"Browser {index}: Error solving Turnstile in {COLORS.get('RED')}{elapsed_time}{COLORS.get('RESET')} Seconds")
        except Exception as e:
            elapsed_time = round(time.time() - start_time, 3)
            await save_result(task_id, "turnstile", {"value": "CAPTCHA_FAIL", "elapsed_time": elapsed_time})
            if self.debug:
                logger.error(f"Browser {index}: Error solving Turnstile: {str(e)}")
        finally:
            if self.debug:
                logger.debug(f"Browser {index}: Closing browser context and cleaning up")
            
            if context is not None:
                try:
                    await context.close()
                    if self.debug:
                        logger.debug(f"Browser {index}: Context closed successfully")
                except Exception as e:
                    if self.debug:
                        logger.warning(f"Browser {index}: Error closing context: {str(e)}")
            
            try:
                if hasattr(browser, 'is_connected') and browser.is_connected():
                    await self.browser_pool.put((index, browser, browser_config))
                    if self.debug:
                        logger.debug(f"Browser {index}: Browser returned to pool")
                else:
                    if self.debug:
                        logger.warning(f"Browser {index}: Browser disconnected, not returning to pool")
            except Exception as e:
                if self.debug:
                    logger.warning(f"Browser {index}: Error returning browser to pool: {str(e)}")






    async def process_turnstile(self):
        """Handle the /turnstile endpoint requests."""
        url = request.args.get('url')
        sitekey = request.args.get('sitekey')
        action = request.args.get('action')
        cdata = request.args.get('cdata')

        if not url or not sitekey:
            return jsonify({
                "errorId": 1,
                "errorCode": "ERROR_WRONG_PAGEURL",
                "errorDescription": "Both 'url' and 'sitekey' are required"
            }), 200

        task_id = str(uuid.uuid4())
        await save_result(task_id, "turnstile", {
            "status": "CAPTCHA_NOT_READY",
            "createTime": int(time.time()),
            "url": url,
            "sitekey": sitekey,
            "action": action,
            "cdata": cdata
        })

        try:
            asyncio.create_task(self._solve_turnstile(task_id=task_id, url=url, sitekey=sitekey, action=action, cdata=cdata))

            if self.debug:
                logger.debug(f"Request completed with taskid {task_id}.")
            return jsonify({
                "errorId": 0,
                "taskId": task_id
            }), 200
        except Exception as e:
            logger.error(f"Unexpected error processing request: {str(e)}")
            return jsonify({
                "errorId": 1,
                "errorCode": "ERROR_UNKNOWN",
                "errorDescription": str(e)
            }), 200

    async def get_result(self):
        """Return solved data"""
        task_id = request.args.get('id')

        if not task_id:
            return jsonify({
                "errorId": 1,
                "errorCode": "ERROR_WRONG_CAPTCHA_ID",
                "errorDescription": "Invalid task ID/Request parameter"
            }), 200

        result = await load_result(task_id)
        if not result:
            return jsonify({
                "errorId": 1,
                "errorCode": "ERROR_CAPTCHA_UNSOLVABLE",
                "errorDescription": "Task not found"
            }), 200

        if result == "CAPTCHA_NOT_READY" or (isinstance(result, dict) and result.get("status") == "CAPTCHA_NOT_READY"):
            return jsonify({"status": "processing"}), 200

        if isinstance(result, dict) and result.get("value") == "CAPTCHA_FAIL":
            return jsonify({
                "errorId": 1,
                "errorCode": "ERROR_CAPTCHA_UNSOLVABLE",
                "errorDescription": "Workers could not solve the Captcha"
            }), 200

        if isinstance(result, dict) and result.get("value") and result.get("value") != "CAPTCHA_FAIL":
            return jsonify({
                "errorId": 0,
                "status": "ready",
                "solution": {
                    "token": result["value"]
                }
            }), 200
        else:
            return jsonify({
                "errorId": 1,
                "errorCode": "ERROR_CAPTCHA_UNSOLVABLE",
                "errorDescription": "Workers could not solve the Captcha"
            }), 200

    

    @staticmethod
    async def index():
        """Serve the API documentation page."""
        return """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Turnstile Solver API</title>
                <script src="https://cdn.tailwindcss.com"></script>
            </head>
            <body class="bg-gray-900 text-gray-200 min-h-screen flex items-center justify-center">
                <div class="bg-gray-800 p-8 rounded-lg shadow-md max-w-2xl w-full border border-red-500">
                    <h1 class="text-3xl font-bold mb-6 text-center text-red-500">Welcome to Turnstile Solver API</h1>

                    <p class="mb-4 text-gray-300">To use the turnstile service, send a GET request to 
                       <code class="bg-red-700 text-white px-2 py-1 rounded">/turnstile</code> with the following query parameters:</p>

                    <ul class="list-disc pl-6 mb-6 text-gray-300">
                        <li><strong>url</strong>: The URL where Turnstile is to be validated</li>
                        <li><strong>sitekey</strong>: The site key for Turnstile</li>
                    </ul>

                    <div class="bg-gray-700 p-4 rounded-lg mb-6 border border-red-500">
                        <p class="font-semibold mb-2 text-red-400">Example usage:</p>
                        <code class="text-sm break-all text-red-300">/turnstile?url=https://example.com&sitekey=sitekey</code>
                    </div>


                    <div class="bg-gray-700 p-4 rounded-lg mb-6">
                        <p class="text-gray-200 font-semibold mb-3">📢 Connect with Us</p>
                        <div class="space-y-2 text-sm">
                            <p class="text-gray-300">
                                📢 <strong>Channel:</strong> 
                                <a href="https://t.me/D3_vin" class="text-red-300 hover:underline">https://t.me/D3_vin</a> 
                                - Latest updates and releases
                            </p>
                            <p class="text-gray-300">
                                💬 <strong>Chat:</strong> 
                                <a href="https://t.me/D3vin_chat" class="text-red-300 hover:underline">https://t.me/D3vin_chat</a> 
                                - Community support and discussions
                            </p>
                            <p class="text-gray-300">
                                📁 <strong>GitHub:</strong> 
                                <a href="https://github.com/D3-vin" class="text-red-300 hover:underline">https://github.com/D3-vin</a> 
                                - Source code and development
                            </p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
        """


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Turnstile API Server")

    parser.add_argument('--no-headless', action='store_true', help='Run the browser with GUI (disable headless mode). By default, headless mode is enabled.')
    parser.add_argument('--useragent', type=str, help='User-Agent string (if not specified, random configuration is used)')
    parser.add_argument('--debug', action='store_true', help='Enable or disable debug mode for additional logging and troubleshooting information (default: False)')
    parser.add_argument('--browser_type', type=str, default='chromium', help='Specify the browser type for the solver. Supported options: chromium, chrome, msedge, camoufox (default: chromium)')
    parser.add_argument('--thread', type=int, default=4, help='Set the number of browser threads to use for multi-threaded mode. Increasing this will speed up execution but requires more resources (default: 1)')
    parser.add_argument('--proxy', action='store_true', help='Enable proxy support for the solver (Default: False)')
    parser.add_argument('--random', action='store_true', help='Use random User-Agent and Sec-CH-UA configuration from pool')
    parser.add_argument('--browser', type=str, help='Specify browser name to use (e.g., chrome, firefox)')
    parser.add_argument('--version', type=str, help='Specify browser version to use (e.g., 139, 141)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Specify the IP address where the API solver runs. (Default: 127.0.0.1)')
    parser.add_argument('--port', type=str, default=os.getenv('SOLVER_PORT', '5073'), help='Set the port for the API solver to listen on. (Default: SOLVER_PORT env or 5073)')
    return parser.parse_args()


def create_app(headless: bool, useragent: str, debug: bool, browser_type: str, thread: int, proxy_support: bool, use_random_config: bool, browser_name: str, browser_version: str) -> Quart:
    server = TurnstileAPIServer(headless=headless, useragent=useragent, debug=debug, browser_type=browser_type, thread=thread, proxy_support=proxy_support, use_random_config=use_random_config, browser_name=browser_name, browser_version=browser_version)
    return server.app


if __name__ == '__main__':
    args = parse_args()
    browser_types = [
        'chromium',
        'chrome',
        'msedge',
        'camoufox',
    ]
    if args.browser_type not in browser_types:
        logger.error(f"Unknown browser type: {COLORS.get('RED')}{args.browser_type}{COLORS.get('RESET')} Available browser types: {browser_types}")
    else:
        app = create_app(
            headless=not args.no_headless, 
            debug=args.debug, 
            useragent=args.useragent, 
            browser_type=args.browser_type, 
            thread=args.thread, 
            proxy_support=args.proxy,
            use_random_config=args.random,
            browser_name=args.browser,
            browser_version=args.version
        )
        app.run(host=args.host, port=int(args.port))
