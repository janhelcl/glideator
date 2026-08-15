import React from 'react';
import {
  Box,
  Link,
  List,
  ListItem,
  ListItemText,
  Paper,
  Typography,
} from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';

const LAST_UPDATED = 'August 15, 2026';

const LegalLayout = ({ title, description, children }) => (
  <Box sx={{ maxWidth: 900, mx: 'auto', p: { xs: 1.5, sm: 2 }, minHeight: '100%' }}>
    <Helmet>
      <title>{title} – Parra-Glideator</title>
      <meta name="description" content={description} />
    </Helmet>
    <Paper elevation={2} sx={{ p: { xs: 2.5, sm: 4 }, borderRadius: 3 }}>
      <Typography variant="h3" component="h1" sx={{ fontWeight: 'bold', mb: 1 }}>
        {title}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Last updated: {LAST_UPDATED}
      </Typography>
      {children}
    </Paper>
  </Box>
);

const Section = ({ title, children }) => (
  <Box sx={{ mt: 3 }}>
    <Typography variant="h5" component="h2" sx={{ fontWeight: 'bold', mb: 1 }}>
      {title}
    </Typography>
    {children}
  </Box>
);

const BulletList = ({ items }) => (
  <List dense disablePadding sx={{ pl: 2 }}>
    {items.map((item) => (
      <ListItem key={item} disableGutters sx={{ alignItems: 'flex-start', py: 0.35 }}>
        <ListItemText
          primary={`• ${item}`}
          primaryTypographyProps={{ variant: 'body1' }}
        />
      </ListItem>
    ))}
  </List>
);

export const Privacy = () => (
  <LegalLayout
    title="Privacy Policy"
    description="How Parra-Glideator handles data on the website and through its public MCP server."
  >
    <Typography variant="body1" paragraph>
      Parra-Glideator is a paragliding decision-support service. This policy describes the data
      handled by the website and by the public Model Context Protocol (MCP) server at
      {' '}<Box component="span" sx={{ fontFamily: 'monospace' }}>https://www.parra-glideator.com/mcp</Box>.
    </Typography>

    <Section title="Data used to provide the service">
      <BulletList items={[
        'MCP requests may contain site IDs or names, dates, XC thresholds, filters, and—only when supplied by the user—latitude and longitude used for distance filtering.',
        'If you create a website account, Parra-Glideator processes the account and profile information needed to operate that account and features such as favorites and notifications.',
        'The service processes forecast, historical flight, site, launch/landing, and curated resource data to answer requests. Some results contain links to third-party websites.',
      ]} />
    </Section>

    <Section title="Product analytics">
      <Typography variant="body1" paragraph>
        The website uses first-party product analytics to understand how features are used. It
        creates a random anonymous identifier in local storage and a random session identifier in
        session storage, and may record the page path, event name, and limited event properties.
        Client-side analytics filters common fields such as email addresses, user-agent strings,
        IP-address fields, and precise coordinate fields from event properties.
      </Typography>
      <Typography variant="body1" paragraph>
        The analytics endpoint uses the request IP address transiently for rate limiting. The
        website does not send product analytics when Global Privacy Control is enabled or the
        browser sends a supported Do Not Track signal.
      </Typography>
    </Section>

    <Section title="Operational data and retention">
      <Typography variant="body1" paragraph>
        Operational logs may contain technical request metadata and errors needed to run and debug
        the service. Account data is retained while it is needed to provide the account features.
        Product analytics and operational data are retained only as long as reasonably needed to
        operate, secure, understand, and improve the service; no permanent retention is intended.
      </Typography>
    </Section>

    <Section title="Third-party services">
      <Typography variant="body1" paragraph>
        Parra-Glideator runs on third-party infrastructure and may link to external clubs,
        meteostations, webcams, map providers, or other resources. When you open an external link,
        that provider's privacy practices apply. ChatGPT and other MCP clients also handle your
        conversation according to their own terms and privacy policies.
      </Typography>
    </Section>

    <Section title="Your choices and requests">
      <Typography variant="body1" paragraph>
        You can use browser privacy controls to disable the website analytics described above. For
        account or privacy requests, use the in-product Feedback page while signed in. For general
        service questions, see the <Link component={RouterLink} to="/support">Support page</Link>.
        Do not post sensitive personal information in public GitHub issues.
      </Typography>
    </Section>
  </LegalLayout>
);

export const Terms = () => (
  <LegalLayout
    title="Terms of Service"
    description="Terms for using Parra-Glideator and its public MCP server."
  >
    <Typography variant="body1" paragraph>
      By using Parra-Glideator, including its public MCP server, you agree to use the service as
      informational decision support and to take responsibility for your own flying decisions.
    </Typography>

    <Section title="Decision support, not a safety service">
      <Typography variant="body1" paragraph>
        Parra-Glideator estimates flight and XC potential from weather forecasts, historical flight
        activity, and site data. Scores, probabilities, rankings, historical analogues, AI answers,
        and other outputs are not a determination that conditions are safe, legal, or suitable for
        a particular pilot.
      </Typography>
      <Typography variant="body1" paragraph>
        Before flying, verify current and local weather, wind, airspace, NOTAMs where applicable,
        site rules, access, hazards, equipment, and suitability for your skills and experience. Use
        authoritative local information and qualified instruction where appropriate.
      </Typography>
    </Section>

    <Section title="Forecasts and site information can be wrong">
      <Typography variant="body1" paragraph>
        Forecasts change, models have errors, historical activity is not a guarantee of future
        conditions, and site information can become incomplete or outdated. Third-party links and
        resources are provided for convenience and are controlled by their respective operators.
      </Typography>
    </Section>

    <Section title="Acceptable use">
      <BulletList items={[
        'Do not attempt to disrupt, overload, probe, or bypass access controls or rate limits on the service.',
        'Do not use the service in a way that violates applicable law or the rights of others.',
        'Automated use of the public MCP endpoint should be reasonable and compatible with normal interactive planning workflows.',
      ]} />
    </Section>

    <Section title="Availability and changes">
      <Typography variant="body1" paragraph>
        The service is provided on a best-effort basis and may change, be unavailable, or contain
        errors. Features, data sources, coverage, and these terms may be updated as the public beta
        evolves. Material changes will be reflected by the updated date on this page.
      </Typography>
    </Section>

    <Section title="Open-source code">
      <Typography variant="body1" paragraph>
        Source code made available in the public Parra-Glideator repository is governed by the
        license included with that repository. These Terms govern use of the hosted service.
      </Typography>
    </Section>
  </LegalLayout>
);

export const Support = () => (
  <LegalLayout
    title="Support"
    description="Support and troubleshooting options for Parra-Glideator and its MCP integration."
  >
    <Typography variant="body1" paragraph>
      For product questions, MCP setup, or troubleshooting, start with the resources below.
    </Typography>

    <Section title="Product and MCP documentation">
      <Typography variant="body1" paragraph>
        The <Link component={RouterLink} to="/about#mcp">How It Works page</Link> explains the
        prediction model and the MCP integration. The public MCP endpoint is
        {' '}<Box component="span" sx={{ fontFamily: 'monospace' }}>https://www.parra-glideator.com/mcp</Box>.
      </Typography>
    </Section>

    <Section title="Report a bug or integration problem">
      <Typography variant="body1" paragraph>
        Use the public{' '}
        <Link
          href="https://github.com/janhelcl/glideator/issues"
          target="_blank"
          rel="noopener noreferrer"
        >
          Glideator GitHub issue tracker
        </Link>
        {' '}for reproducible bugs, MCP client compatibility issues, or feature requests. Please do
        not include passwords, tokens, private conversation content, or other sensitive personal
        information in a public issue.
      </Typography>
    </Section>

    <Section title="Account or privacy request">
      <Typography variant="body1" paragraph>
        If you have a Parra-Glideator account, use the <Link component={RouterLink} to="/feedback">in-product Feedback page</Link>
        {' '}while signed in so the request can be associated with your account without exposing it
        publicly.
      </Typography>
    </Section>

    <Section title="Before reporting an MCP problem">
      <BulletList items={[
        'Confirm the MCP URL is exactly https://www.parra-glideator.com/mcp.',
        'Include the MCP client you are using and the approximate time of the failure.',
        'Include the tool name and non-sensitive arguments when possible, but remove tokens or private data.',
      ]} />
    </Section>
  </LegalLayout>
);
