module.exports = function(eleventyConfig) {
	eleventyConfig.addPassthroughCopy({"__static/images":"images"});
	eleventyConfig.addShortcode("card", (data) => {
		let link = data.link
		let logo = data.logo
		let entries = data.entries
		let result = `<center><a target="_blank" href="${link}"><img src="${logo}"/></a></center>
<br/>
<div class="box">`
		entries.forEach( (e) => {
			result += `
<div class="linkclass">
<a target="_blank" href="${e.link}">${e.title}</a>
</div>`
		})
		result += `</div>
<br/>`
		return result
	});
}