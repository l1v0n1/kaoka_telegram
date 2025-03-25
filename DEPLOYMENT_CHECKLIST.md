# Deployment Checklist

Use this checklist to ensure your bot is ready for deployment.

## Configuration

- [ ] Updated `config.py` with your Telegram Bot API token (or configured environment variable)
- [ ] Set up admin IDs in `config.py` or via environment variables
- [ ] Configured admin username and chat ID
- [ ] Set up QIWI payment details if using payment features

## Database

- [ ] MongoDB installed and running
- [ ] Created database named 'baraboba'
- [ ] Created collection named 'posts'
- [ ] Unique index created on 'chat_id' field (this is done automatically on first run)

## Environment

- [ ] Python 3.7+ installed
- [ ] Virtual environment created and activated
- [ ] All dependencies installed from `requirements.txt`

## Deployment Options

### Standard Deployment

- [ ] Configured running environment (systemd service, screen, or other method for keeping the bot running)
- [ ] Set up logging directory with proper permissions
- [ ] Checked firewall rules if necessary

### Docker Deployment

- [ ] Docker and Docker Compose installed
- [ ] Created `.env` file with configuration values
- [ ] Verified Docker containers can access MongoDB
- [ ] Set up Docker to restart on system boot if needed

## Testing

- [ ] Verified bot responds to /start command
- [ ] Tested user registration flow
- [ ] Tested profile viewing and rating
- [ ] Tested admin commands (if you are an admin)
- [ ] Tested payment processing (if using)

## Backup

- [ ] Set up regular MongoDB backups
- [ ] Documented restore procedure

## Monitoring

- [ ] Set up monitoring for bot uptime
- [ ] Configured alerts for errors or downtime

---

Once you've completed all the necessary steps, your bot should be ready for deployment! 