import unittest
from provoke.config import evaluate_page_quality


class TestQualityFilter(unittest.TestCase):
    def test_personal_blog(self):
        url = "https://danluu.com/productivity/"
        html = (
            """
        <html>
        <head>
            <title>Productivity</title>
            <link rel="alternate" type="application/rss+xml" href="/atom.xml">
        </head>
        <body>
            <h1>Productivity</h1>
            <p>I've been thinking about productivity lately. Many people ask me how I get so much done.</p>
            <p>First, I try to avoid meetings. Meetings are a waste of time generally. I prefer async communication.</p>
            <p>When I was working at Google, I noticed that the most productive people weren't the ones who worked the longest hours. 
            Instead, they were the ones who were best at prioritizing their work and saying no to unimportant tasks. 
            This is something that I've tried to emulate in my own life.</p>
            <p>I also think it's important to have a good workspace. For me, that means a quiet room with a comfortable chair and a large monitor. 
            Some people prefer working in coffee shops, but I find the noise too distracting. It's all about finding what works for you.</p>
            <p>Another key factor is getting enough sleep. I try to get at least eight hours of sleep every night. 
            If I don't get enough sleep, I find it much harder to concentrate and I'm much less productive. 
            It's better to work fewer hours and be more focused than to work more hours and be tired.</p>
            <p>Finally, I think it's important to take breaks. I try to take a short break every hour or so to stretch and move around. 
            This helps to keep me energized and prevents me from getting burnt out. 
            Even just a few minutes of walking can make a big difference.</p>
            """
            + "<p>This is a filler sentence to reach the minimum word count requirement for the test case.</p>"
            * 30
            + """
            <p>Last updated: January 15, 2024</p>
            <div class="author">By Dan Luu</div>
        </body>
        </html>
        """
        )
        text = (
            "Productivity. I've been thinking about productivity lately. Many people ask me how I get so much done. "
            + "First, I try to avoid meetings. Meetings are a waste of time generally. I prefer async communication. When I was working at Google, I noticed that the most productive people weren't the ones who worked the longest hours. Instead, they were the ones who were best at prioritizing their work and saying no to unimportant tasks. This is something that I've tried to emulate in my own life. I also think it's important to have a good workspace. For me, that means a quiet room with a comfortable chair and a large monitor. Some people prefer working in coffee shops, but I find the noise too distracting. It's all about finding what works for you. Another key factor is getting enough sleep. I try to get at least eight hours of sleep every night. If I don't get enough sleep, I find it much harder to concentrate and I'm much less productive. It's better to work fewer hours and be more focused than to work more hours and be tired. Finally, I think it's important to take breaks. I try to take a short break every hour or so to stretch and move around. This helps to keep me energized and prevents me from getting burnt out. Even just a few minutes of walking can make a big difference. "
            + "This is a filler sentence to reach the minimum word count requirement for the test case. "
            * 30
            + " Last updated: January 15, 2024. By Dan Luu."
        )

        result = evaluate_page_quality(url, html, text)
        self.assertTrue(
            result["is_acceptable"],
            f"Should accept personal blog. Reasons: {result['rejection_reasons']}",
        )
        self.assertGreaterEqual(result["scores"]["personal_signals"], 3)

    def test_corporate_marketing(self):
        url = "https://www.salesforce.com/blog/customer-success/"
        html = (
            """
        <html>
        <head>
            <title>How to Drive Customer Success</title>
            <script src="https://js.hs-scripts.com/123.js"></script>
            <script src="https://static.ads-twitter.com/uwt.js"></script>
        </head>
        <body>
            <h1>Customer Success Strategies</h1>
            <p>In today's fast-paced market, businesses need a robust CRM to manage customer relationships effectively. 
            Our solutions provide a 360-degree view of your customers.</p>
            <p>Book a demo today to see how we can help your enterprise grow.</p>
            <button>Get Started Free Trial</button>
            <button>Talk to Sales</button>
            <button>Request Demo</button>
            <button>Schedule a Call</button>
            <button>Contact Sales</button>
            """
            + "<p>CRM Solutions </p>" * 100
            + """
            <p>© 2024 Salesforce. All rights reserved.</p>
        </body>
        </html>
        """
        )
        text = (
            "Customer Success Strategies In today's fast-paced market, businesses need a robust CRM. Book a demo. Get Started Free Trial Talk to Sales Request Demo Schedule a Call Contact Sales "
            + "CRM Solutions " * 100
        )

        result = evaluate_page_quality(url, html, text)
        self.assertFalse(result["is_acceptable"], "Should reject corporate marketing")
        self.assertIn("Corporate page", str(result["rejection_reasons"]))

    def test_low_text_ratio(self):
        url = "https://example.com/gallery"
        html = "<html><body>" + "<div><img src='p.jpg'></div>" * 50 + "</body></html>"
        text = "Image Gallery"
        result = evaluate_page_quality(url, html, text)
        self.assertFalse(result["is_acceptable"])
        self.assertTrue(any("ratio" in r for r in result["rejection_reasons"]))

    def test_too_short(self):
        url = "https://example.com/short"
        html = "<html><body><p>Hello world. This is too short.</p></body></html>"
        text = "Hello world. This is too short."
        result = evaluate_page_quality(url, html, text)
        self.assertFalse(result["is_acceptable"])
        self.assertTrue(any("length" in r for r in result["rejection_reasons"]))


if __name__ == "__main__":
    unittest.main()
