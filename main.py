const { Client, Intents } = require('discord.js-selfbot'); // Import discord.js-selfbot
const { createLogger, format, transports } = require('winston');
const axios = require('axios');
const { URLSearchParams } = require('url');

// Configuration
const TOKEN = ''; // Your own Discord token
const CHANNEL_ID = ''; // The Poké2Café bot's channel ID
const DELAY = 2; // Seconds between interactions
const EVENTS = ['Applin', 'Falinks', 'Bellibolt', 'Gulpin', 'Spheals', 'Clamacaron', 'Goomy', 'Tangela', 'Alopix', 'Doublade'];
const DEBUG = false;

// Logger setup
const logger = createLogger({
  level: 'info',
  format: format.combine(
    format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
    format.printf(info => `${info.timestamp} [${info.level.toUpperCase()}] ${info.message}`)
  ),
  transports: [
    new transports.Console(),
    new transports.File({ filename: 'pokecafe.log' }),
  ],
});

// Helper functions
const generateSessionId = () => {
  const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  return Array.from({ length: 16 }).map(() => characters.charAt(Math.floor(Math.random() * characters.length))).join('');
};

const clickButton = async (messageId, customId, channelId, guildId, applicationId, sessionId, type, value = '') => {
  try {
    const params = new URLSearchParams({
      custom_id: customId,
      component_type: type,
      guild_id: guildId,
      application_id: applicationId,
      channel_id: channelId,
      message_id: messageId,
      session_id: sessionId,
      value: value
    });
    const response = await axios.post(`https://discord.com/api/v10/interactions/${messageId}/${customId}/callback`, params, {
      headers: {
        Authorization: `Bot ${TOKEN}`
      }
    });
    return response.status;
  } catch (error) {
    logger.error('Error clicking button:', error);
    return -1;
  }
};

const extractDishName = (messageContent) => {
  const match = messageContent.match(/You've completed the order for (.+)\./);
  return match ? match[1] : null;
};

const checkAvailableIngredients = (ingredients) => {
  const minQuantity = Math.min(...Object.values(ingredients).map(Number));
  return minQuantity > 0 ? minQuantity : 0;
};

class BotClient extends Client {
  constructor() {
    super({ intents: [Intents.FLAGS.GUILDS, Intents.FLAGS.GUILD_MESSAGES, Intents.FLAGS.GUILD_MESSAGE_REACTIONS] });
    this.availableIngredients = {};
    this.eventMons = 0;
    this.pokecoins = 0;
    this.shards = 0;
    this.redeems = 0;
  }

  async onReady() {
    logger.info(`Successfully Logged into ${this.user.tag}`);
    logger.warning('PLEASE MAKE SURE YOUR CURRENT ORDERS ARE FINISHED!');
    if (CHANNEL_ID === '') {
      logger.critical('Please set a ChannelId and restart the program...');
      process.exit();
    }
    if (DELAY <= 1) {
      logger.warning('Delay is set to less than or equal to 1, This can cause rate-limit issues...');
    }
    if (!DEBUG) {
      this.sendCommand('<@716390085896962058> ev inv');
    } else {
      const channel = this.channels.cache.get(CHANNEL_ID);
      const message = await channel.messages.fetch(12354);
      console.log(message.embeds[0].toJSON());
      process.exit(); // Stop here for debugging
    }
  }

  async onMessage(message) {
    if (message.author.id === '716390085896962058' && message.channel.id === parseInt(CHANNEL_ID)) {
      if (message.embeds.length > 0 && message.embeds[0].title === 'Welcome to Poké2Café!') {
        const easyButton = message.components.at(0)?.children.at(0);
        if (message.components.length > 1) {
          const customId = easyButton.custom_id;
          const guildId = message.guild.id.toString();
          const type = 3;
          const channelId = message.channel.id.toString();
          const applicationId = this.user.id.toString(); // Use your own user ID here
          const option = easyButton.options.at(0);
          const [idx, ind, v, availableIngredients] = this.checkIngredients(easyButton.options);
          if (idx !== 999) {
            const sessionId = generateSessionId();
            logger.warning(`SessionId: ${sessionId}`);
            const buttonResult = await clickButton(
              message.id.toString(),
              customId,
              channelId,
              guildId,
              applicationId,
              sessionId,
              type,
              v
            );
            logger.info(`Button Request Result (200/204/202 is good): ${buttonResult}`);
            this.sendCommand(`<@716390085896962058> ev use ${ind}`);
            await new Promise(resolve => setTimeout(resolve, DELAY * 1000));
            logger.info('Starting another round...');
            this.sendCommand('<@716390085896962058> ev');
          } else {
            logger.info('Finished all Recipes/Ran out of materials for the current order...');
            logger.info(`Pokecoins: ${this.pokecoins}`);
            logger.info(`Shards: ${this.shards}`);
            logger.info(`Redeems: ${this.redeems}`);
            logger.info(`Events: ${this.eventMons}`);
          }
        } else {
          logger.info('Finished all Recipes/Ran out of materials for the current order...');
          logger.info(`Pokecoins: ${this.pokecoins}`);
          logger.info(`Shards: ${this.shards}`);
          logger.info(`Redeems: ${this.redeems}`);
          logger.info(`Events: ${this.eventMons}`);
        }
      }

      if (message.content.includes('You've completed the order')) {
        logger.info(`Successfully Completed Order for ${extractDishName(message.content)}...`);
        if (message.embeds.length > 0) {
          const embed = message.embeds[0];
          const embedDesc = embed.description;
          for (const eventMon of EVENTS) {
            if (embedDesc.includes(eventMon)) {
              this.eventMons++;
              break;
            }
          }
          if (embedDesc.includes('Shards') || embedDesc.includes('Pokécoins')) {
            const pattern = /<:\w+:\d+>\s*([\d,]+)\s*(\w+)/;
            const match = embedDesc.match(pattern);
            if (match) {
              const amount = parseInt(match[1].replace(',', ''), 10);
              const type = match[2];
              if (type === 'Shards') {
                this.shards += amount;
              } else if (type === 'Pokécoins') {
                this.pokecoins += amount;
              }
            }
          }
          if (embedDesc.includes('Redeem')) {
            const pattern = /([\d,]+)\s+(\w+)/;
            const match = embedDesc.match(pattern);
            if (match) {
              const amount = parseInt(match[1].replace(',', ''), 10);
              this.redeems += amount;
            }
          }
        }
      }

      if (message.embeds.length > 0 && message.embeds[0].title.includes('You donate your ingredients')) {
        const raw = message.embeds[0].description.split('\n');
        for (const line of raw) {
          for (const eventMon of EVENTS) {
            if (line.includes(eventMon)) {
              this.eventMons++;
              continue;
            }
          }
          if (line.includes('Shards') || line.includes('Pokécoins')) {
            const pattern = /<:\w+:\d+>\s*([\d,]+)\s*(\w+)/;
            const match = line.match(pattern);
            if (match) {
              const amount = parseInt(match[1].replace(',', ''), 10);
              const type = match[2];
              if (type === 'Shards') {
                this.shards += amount;
              } else if (type === 'Pokécoins') {
                this.pokecoins += amount;
              }
            }
          }
          if (line.includes('Redeem')) {
            const pattern = /([\d,]+)\s+(\w+)/;
            const match = line.match(pattern);
            if (match) {
              const amount = parseInt(match[1].replace(',', ''), 10);
              this.redeems += amount;
            }
          }
        }
      }

      if (message.embeds.length > 0 && message.embeds[0].title.includes('Poké2Café Ingredients Inventory')) {
        const text = message.embeds[0].fields[0].value;
        const ingredientDict = {};
        const ingredientValues = text.matchAll(/`([^`]+)`\s+`([^`]+)`/g);
        for (const [_, ingredient, quantity] of ingredientValues) {
          ingredientDict[ingredient.trim()] = parseInt(quantity.trim(), 10);
        }
        const minQuantity = checkAvailableIngredients(ingredientDict);
        if (minQuantity > 0) {
          let totalQuantity = minQuantity;
          while (totalQuantity > 0) {
            const donationQuantity = Math.min(totalQuantity, 15);
            this.sendCommand(`<@716390085896962058> ev donate ${donationQuantity}`);
            logger.warning('Sleeping for 6 seconds...');
            await new Promise(resolve => setTimeout(resolve, 6000));
            totalQuantity -= donationQuantity;
          }
          this.availableIngredients = Object.fromEntries(Object.entries(ingredientDict).map(([ingredient, quantity]) => [ingredient, quantity - minQuantity]));
          this.availableIngredients = Object.fromEntries(Object.entries(this.availableIngredients).filter(([_, quantity]) => quantity > 0));
          this.sendCommand('<@716390085896962058> ev');
        } else {
          this.availableIngredients = ingredientDict;
          this.availableIngredients = Object.fromEntries(Object.entries(this.availableIngredients).filter(([_, quantity]) => quantity > 0));
          logger.warning('Ingredients are over. Proceeding to recipes...');
          this.sendCommand('<@716390085896962058> ev');
        }
      }

      if (message.content.includes('Are you sure you want to donate')) {
        const easyButton = message.components.at(0)?.children.at(0);
        const customId = easyButton.custom_id;
        const guildId = message.guild.id.toString();
        const sessionId = generateSessionId();
        const type = 2;
        const channelId = message.channel.id.toString();
        const applicationId = this.user.id.toString(); // Use your own user ID here
        logger.info(`Button Request Result (200/204/202 is good): ${await clickButton(
          message.id.toString(),
          customId,
          channelId,
          guildId,
          applicationId,
          sessionId,
          type
        )}`);
      }
    }
  }

  checkIngredients(options) {
    const ingredients = {};
    for (const option of options) {
      const ingredient = option.label.split('x')[0].trim();
      const quantity = parseInt(option.label.split('x')[1].trim(), 10);
      if (this.availableIngredients[ingredient]) {
        if (this.availableIngredients[ingredient] >= quantity) {
          ingredients[ingredient] = quantity;
        } else {
          ingredients[ingredient] = this.availableIngredients[ingredient];
        }
      }
    }
    const minQuantity = checkAvailableIngredients(ingredients);
    if (minQuantity > 0) {
      const sortedIngredients = Object.entries(ingredients).sort((a, b) => b[1] - a[1]);
      for (let i = 0; i < sortedIngredients.length; i++) {
        const [ingredient, quantity] = sortedIngredients[i];
        if (quantity >= minQuantity) {
          return [i, ingredient, quantity, ingredients];
        }
      }
    }
    return [999, '', 0, ingredients];
  }

  sendCommand(command) {
    const channel = this.channels.cache.get(parseInt(CHANNEL_ID));
    if (channel) {
      channel.send(command);
    } else {
      logger.error(`Channel not found: ${CHANNEL_ID}`);
    }
  }
}

const startBot = () => {
  const client = new BotClient();
  client.login(TOKEN);
};

if (require.main === module) {
  startBot();
}
