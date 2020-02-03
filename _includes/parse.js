let Parser = require('rss-parser');
let parser = new Parser();

module.exports = async (url) => {
	try {
		let feed = await parser.parseURL(url);
		
		feed.items.forEach(item => {
			console.log(item.title);
			console.log(item.link);
		});
	} catch (error) {
		console.log(error)
	}
};