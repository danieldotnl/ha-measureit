# Measure It
MeasureIt can measure all kind of things happening in Home Assistant based on time and templates.

Some examples of use cases:
- Measure the daily shower duration
- Measure the number of planes during the night flying over your home (e.g. in combination with [this awesome integration](https://github.com/AlexandrErohin/home-assistant-flightradar24)).
- Measure the time your kids are watching tv every day
- Measure how many times the door opens when the AC is on

Some of the use cases can also be achieved with the `history_stats` integration, but MeasureIt is much simpler to set up, and can measure only when a template evaluates to true. There are also some similarities with the way the `utility_meter` is working.

## Automated Installation Using HACS

![hacs_badge](https://img.shields.io/badge/HACS-Default-orange)
![hacs installs](https://img.shields.io/endpoint.svg?url=https%3A%2F%2Flauwbier.nl%2Fhacs%2Fmeasureit)

[![Install quickly via a HACS link](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=danieldotnl&repository=ha-measureit&category=integration)

MeasureIt is included the standard HACS repositories. Install it via the standard steps, or quickly with the button above:
* Search for MeasureIt in the Integrations section of HACS,
* Choose 'MeasureIt' and select the Download button,
* Restart HomeAssistant to complete the installation.

## Configuration
I spent a lot of time on the config flow to make it as convenient as possible, but I will provide some further explanation here.

![4f11475e065068a10f4b3ba958ffd2a79d1047a6](https://github.com/danieldotnl/ha-measureit/assets/2983203/e2d8cafb-12bc-4987-9d89-e330a2903220)

1. In this first screen you can choose WHAT you want to measure. You choose if you want to create a time meter that measure everything time related, or if you want to measure the change of a value of another sensor (e.g. m3 gas consumption).

![efd53d1770af2e4f22de8dc98c5b4259ce06bd9b](https://github.com/danieldotnl/ha-measureit/assets/2983203/1140dab9-3809-4a2e-b97c-1fc851e5dfce)


2. After clicking next you provide a name for the meter, which will be used for logging and as a prefix for the sensor names. If you choose to measure a source sensor, you can configure it here.

![35cdd851781ea60cefe174c30171c3e69d13d7a8](https://github.com/danieldotnl/ha-measureit/assets/2983203/6a27a383-5b40-4def-8f24-378cd4773766)

3. The next screen is the most interesting. Here you configure WHEN your want to measure. First of all a template condition can be provided. E.g.:
```yaml
{{ is_state('media_player.tv', 'on') and is_state('person.daniel', 'away') }}
```
You can also select on which days you want to measure (e.g. only during the week) and a time window.

![061bfae57ef30b2d736fcf6534fef06b7f19319a](https://github.com/danieldotnl/ha-measureit/assets/2983203/3586c5c2-b9d6-4274-979e-4f2b4916b000)

4. After that you configure which sensor you want to create. A sensor shows the measurement for a certain period. E.g. per day/week/month/year.
A `value_template` can be provided like in other sensor to manipulate the value of the sensor, and the usual classes like the `unit_of_measurement`, `device_class`, etc.

Finally, you hit next and the integration will be set up! You will now have your new sensors available. There is also a flow for configuring MeasureIt after it has been set up. You can add/remove sensor or change the main config.
