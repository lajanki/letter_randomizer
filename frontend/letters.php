<!DOCTYPE html>
<!--
A PHP script for showing the letter index at http://lajanki.mbnet.fi/letters as a table sorted by upload date.
22.2.2016
-->

<html>
<head>
	<title>Index of /letters</title>
	<!-- bootstrap -->
	<meta name="viewport" content="width=device-width, initial-scale=1">
	<link rel="stylesheet" href="http://maxcdn.bootstrapcdn.com/bootstrap/3.3.5/css/bootstrap.min.css">
	<script src="https://ajax.googleapis.com/ajax/libs/jquery/1.11.3/jquery.min.js"></script>
	<script src="http://maxcdn.bootstrapcdn.com/bootstrap/3.3.5/js/bootstrap.min.js"></script>
</head>

<body>
<div class="container">

	<div class="row">

	<h1>Index of /letters</h1>

		<!-- create a table to list files -->
		<table>
			<tr>
				<td>File</td>
				<td>Uploaded</td>
			</tr>

		<?php

		// path to files to show
		$base = "templates/";

		// sort in ascending order - this is default
		$files = scandir($base);

		// use usort to sort by time modified
		usort($files, function($a, $b){
			return filemtime("templates/" . $a) < filemtime("templates/" . $b);
		});

		// add files to table
		foreach ($files as $file) {
			if ($file[0] == ".") { continue; }
			$path = $base . $file;  // full path to file
			$modified = date("j.n.Y H:i:s", filemtime($path));
			//$link = "<a href='$path'>$file</a>";

			$link = "<a href=active.php?filename=". urlencode($path). ">$file</a>";  // pass filename to active.php

			// print a new row to the table
			echo "<tr>";
			echo "<td>" . $link . "</td>";
			echo "<td>" . $modified . "</td>";
			echo "</tr>";

		}

		?>

		</table>
	</div>

	<!-- bottom row for sources -->
	<hr/>
	<div class="row">
		<button data-toggle="collapse" data-target="#sources">Sources</button>

		<div id="sources" class="collapse">
			<?php
			// display sources from file as links
			$sources = file("templates/SOURCES");
			foreach($sources as $line) {
				echo "<a href=" . $line . ">" . $line . "</a><br/>";
			}
			?>
		</div>

	</div>

</div>
</body>
</html>
