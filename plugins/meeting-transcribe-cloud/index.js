function register(api) {
  const logger = api && api.logger;
  if (logger && typeof logger.debug === "function") {
    logger.debug("[meeting-transcribe-cloud] config surface loaded");
  }
}

module.exports = register;
module.exports.default = register;
