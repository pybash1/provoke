import unittest
from landing_page_filter import (
    is_service_landing_page,
    is_ecommerce_page,
    is_homepage_not_article,
    detect_spam_services,
)


class TestLandingPageFilter(unittest.TestCase):

    def test_ecommerce_detection(self):
        # Example: Vapehuset (E-commerce)
        html_ecom = """
        <html>
            <body>
                <button>Add to cart</button>
                <div class="payment-icons">
                    <span>Visa</span>
                    <span>Mastercard</span>
                    <span>PayPal</span>
                </div>
            </body>
        </html>
        """
        self.assertTrue(is_ecommerce_page(html_ecom))

        # Example: Product Schema
        html_schema = """
        <html>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org/",
                "@type": "Product",
                "name": "Cool Widget"
            }
            </script>
        </html>
        """
        self.assertTrue(is_ecommerce_page(html_schema))

    def test_spam_service_detection(self):
        # Example: Sidesmedia / BuyCheapestFollowers
        url_spam = "https://buycheapestfollowers.com"
        text_spam = "We offer real instagram followers and tiktok followers. Grow your audience fast."
        self.assertTrue(detect_spam_services(url_spam, text_spam))

        # Example: AI Text Humanizer
        url_tool = "https://ai-text-humanizer.com/"
        text_tool = "Our tool helps you humanize ai text and bypass ai detector. Best paraphrasing tool."
        self.assertTrue(detect_spam_services(url_tool, text_tool))

    def test_service_landing_page_detection(self):
        # Example: IBAN.com or SSL.org
        html_service = """
        <html>
            <body>
                <a href="/signup">Get Started</a>
                <a href="/pricing">Pricing Plans</a>
                <p>We provide enterprise grade security solutions. Starting at $99/month.</p>
                <button>Order Now</button>
            </body>
        </html>
        """
        text_service = "We provide enterprise grade security solutions. Starting at $99/month. Our service is the best. Get started today."
        # path is '/'
        is_service, score = is_service_landing_page(html_service, text_service, "/")
        self.assertTrue(is_service)
        self.assertGreater(score, 8)

    def test_homepage_no_blog_detection(self):
        # Homepage without blog links
        url_home = "https://utility-service.com/"
        html_no_blog = """
        <html>
            <body>
                <nav>
                    <a href="/features">Features</a>
                    <a href="/pricing">Pricing</a>
                    <a href="/contact">Contact</a>
                </nav>
            </body>
        </html>
        """
        self.assertTrue(is_homepage_not_article(url_home, html_no_blog))

        # Homepage WITH blog links
        html_with_blog = """
        <html>
            <body>
                <nav>
                    <a href="/blog/post-1">Post 1</a>
                    <a href="/blog/post-2">Post 2</a>
                    <a href="/posts/post-3">Post 3</a>
                </nav>
            </body>
        </html>
        """
        self.assertFalse(is_homepage_not_article(url_home, html_with_blog))

    def test_legitimate_blog_acceptance(self):
        # Personal blog post
        url_blog = "https://johndoe.dev/posts/2024/debugging-tips"
        text_blog = "In this article I will explain how to debug python code. First we use pdb..."
        html_blog = "<html><body><h1>Debugging Tips</h1><p>Content...</p></body></html>"

        # Should NOT be flagged by these commercial filters
        self.assertFalse(is_ecommerce_page(html_blog))
        self.assertFalse(detect_spam_services(url_blog, text_blog))

        # Check service landing page (should be false)
        is_service, score = is_service_landing_page(html_blog, text_blog, url_blog)
        self.assertFalse(is_service)


if __name__ == "__main__":
    unittest.main()
