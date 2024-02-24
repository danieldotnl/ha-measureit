# Measure It

MeasureIt can measure all kind of things happening in Home Assistant based on time and templates.

Some examples of use cases:

- Measure the daily shower duration
- Measure the number of planes during the night flying over your home
- Measure the time your kids are watching tv every day
- Measure how many times the door opens when the AC is on

MeasureIt has overlap with `history_stats` and `utility_meter` but provides other features as well, is easier to set up and can measure based on conditions and time windows.

Note: you do require some Home Assistant templating knowledge for most use cases. If you need help with this, do not create a Github issue but ask your question on the [community forum](https://community.home-assistant.io/t/measureit-measure-all-you-need-based-on-time-and-templates/660614).

## How does it work?

MeasureIt currently offers 3 different 'meter types' which you can choose from: **time**, **source**, **counter**.

### Time

Time is basically just a timer that runs when all the conditions that you provide in a template are met. You can also configure to only measure during specific times. E.g. only in the weekend, or only during the night. Time meters measure in seconds but the sensors update every minute. E.g. measure when the following template applies `{{ is_state('media_player.tv', 'on') }}`.

### Source

Source meters do listen for state changes in another entity and measure the difference. E.g. listen to the gas consumption sensor, and keep track of how much it changes when the shower is on.

### Counter

A counter meter counts how many times a configured template changes to True. E.g. `{{ is_state('binary_sensor.front_door', 'on') }}` counts each time the front door opens.

The measurements are kept in sensors for different periods that can be configured. So a day sensor will reset each day and a year sensor each year. You can also choose for a sensor that does not reset automatically.\
You can manually reset a sensor at a given time with the `measureit.reset` service.

## Installation (using HACS)

![hacs_badge](https://img.shields.io/badge/HACS-Default-orange)
![hacs installs](https://img.shields.io/endpoint.svg?url=https%3A%2F%2Flauwbier.nl%2Fhacs%2Fmeasureit)

[![Install quickly via a HACS link](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=danieldotnl&repository=ha-measureit&category=integration)

MeasureIt is included the standard HACS repositories. Install it via the standard steps, or quickly with the button above:

- Search for MeasureIt in the Integrations section of HACS,
- Choose 'MeasureIt' and select the Download button,
- Restart HomeAssistant to complete the installation.

## Configuration

Go to Settings -> Devices & services, and hit the '+ add integration' button. Search for MeasureIt and click it to start the configuration flow.
The config flow is descriptive and hopefully as clear and simple as possible.

Do keep in mind that the config flow is guiding you through 3 important steps:

- **What** do you want to measure?
- **When** do you want to measure?
- **How** do you want to measure?

The _what_ is the time, source or counter described above, plus the details required for those. The _when_ is all about the conditions that should be met for measuring. And the _how_ is about the sensors that will be created. Here you pick the periods (e.g. per day/week/year) and for each of those a sensor will be created.\
For the additional sensor properties like unit of measurement, state class and device class, defaults are picked as good as possible. Only change those when you know what you are doing.\
If you want different properties per sensor, you can add additional sensor after setting up MeasureIt, by choosing 'configure' (the options flow) behind you MeasureIt configuration in 'Devices & services'.

## FAQ

#### How do I show time sensors in a different format?

By default, the device class `duration` is applied on time sensors. This, in combination with the unit of measurement `s` (seconds) lets Home Assistant know what this sensor is about. HA will automatically apply an applicable format in the frontend (the format changes depending on the amount). I recommend using this.

If you really think you need a different format, you can do so by providing a value template for the sensor (in the 'how' part of the config). E.g. if you want to show hours, you can divide the state by 3600: `{{ value / 3600 | round }}`. This is still numeric and supports long term statistics.\
You can also change the format in a string format like 'HH:MM'. E.g. with this value template: `{{ value | float | timestamp_custom('%H:%M', false) }}`.\
**Attention**: if you really want this, do not use a device class or a state class. This will format the state in a string and statistics cannot be calculated.

#### How can I show more/less digits for source and time sensors?

MeasureIt is rounding source sensors states to 3 digits and time sensors to seconds. If you need more or less digits, you can do so by providing a value template. The `value` inserted in the value template is not rounded. E.g.: `{{ value }}` will give you all digits.

#### How can I reset a sensor when I need to?

You can reset a sensor manually/via an automation, with the `measureit.reset` service. This service takes the entity ids of the sensors you want to reset, and optionally a future reset datetime. By default, it will reset the sensor immediately.
